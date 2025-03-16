import os
from typing import List, Dict, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import tool
from langchain.tools.render import format_tool_to_openai_function
from langchain.memory import ConversationBufferMemory
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.schema.agent import AgentFinish
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from RagClass2 import RagTool, WebSearchTool
from pathlib import Path
import logging

SCRIPT_DIR = Path.cwd()
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "leadership_coach.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ortam değişkenlerini yükle
load_dotenv()
openai_api_key = os.environ.get("OPENAI_API_KEY")

# Araçları başlat
rag_tool = RagTool()
web_search_tool = WebSearchTool()

# Sabitler
LEADERSHIP_COACH_SYSTEM_PROMPT = """
Sen bir liderlik koçusun ve amacın kullanıcılara rehberlik etmek, ilham vermek ve stratejik düşünmelerine yardımcı olmak. 
Tonun profesyonel, empatik ve ilham verici olmalı. 
Cevaplarını, doğal, yapılandırılmış ve içgörü sunan bir şekilde ver. 
Kullanıcıya bir koç gibi yaklaş, sorularını dikkatle analiz et ve gerektiğinde yönlendirici sorularla derinleştir.
Kullanıcı liderlik ile ilgili bir soru sormuyorsa soruyu anlamaya çalış ve gerektiğinde kullanıcıyı yönlendir.
Cevaplarında somut örnekler ve rehber ilkeler sunmaya özen göster.
Geçmiş sohbeti dikkate alarak tutarlı ve bağlamsal cevaplar ver.
"""

# Modüler Fonksiyonlar
def format_rag_results(rag_results: List[Dict]) -> str:
    return "\n".join([f"Soru: {r['question']}\nCevap: {r['answer']}" for r in rag_results])

def format_web_results(web_results: List[Dict]) -> str:
    return "\n".join([f"Başlık: {r['title']}\nURL: {r['url']}\nÖzet: {r['snippet']}" for r in web_results])

def evaluate_rag_results(user_question: str, rag_results: List[Dict]) -> str:
    if not rag_results:
        print("RAG sonuçları boş.")
        return fallback_to_web_search(user_question)

    llm = ChatOpenAI(temperature=0.3)
    eval_prompt = ChatPromptTemplate.from_messages([
        ("system", """
            Sen bir değerlendirme asistanısın. Görevin, verilen kullanıcı sorusuna RAG sonuçlarının uygun, doğru ve yeterli olup olmadığını kontrol etmek.
            Kriterler:
            - RAG'daki sorular ve cevaplar, kullanıcı sorusuyla anlamsal olarak uyumlu olmalı.
            - Cevaplar yeterli bilgi içermeli (çok kısa veya alakasız olmamalı).
            Çıktı olarak yalnızca 'True' veya 'False' döndür, başka açıklama ekleme.
        """),
        ("user", "Kullanıcı sorusu: {user_question}\nRAG sonuçları: {rag_results}")
    ])

    rag_results_str = format_rag_results(rag_results)
    response = llm(eval_prompt.format_messages(user_question=user_question, rag_results=rag_results_str)).content.strip()

    if response == "True":
        print("RAG sonuçları yeterli ve doğru.")
        ""
        logger.info(f"RAG sonuçları ✅ Yeterli: \n\n ------------ {rag_results_str} ------------ \n\n")
        return rag_results_str
    else:
        print("RAG sonuçları yetersiz veya yanlış.")
        log_web = fallback_to_web_search(user_question)
        logger.info(f"RAG sonuçları ❌ Yetersiz: \n\n ------------ {log_web} ------------ \n\n")
        return log_web

def fallback_to_web_search(user_question: str) -> str:
    try:
        results = web_search_tool.search(
            query=user_question,
            max_results=3,
            include_answer="advanced",
            include_images=False,
            include_image_descriptions=False,
            search_depth="advanced"
        )
        return format_web_results(results['results'])
    except Exception as e:
        print(f"Web araması başarısız: {e}")
        return "Web araması yapılamadı."

# Pydantic Model
class UserQuestion(BaseModel):
    userQuestion: str = Field(description="Kullanıcının sorduğu soru", example="Nasıl lider olunur?")
    leaderShip: bool = Field(description="Sorunun liderlikle alakalı olup olmadığını belirler.", example=True)

# Tool Tanımı
@tool(args_schema=UserQuestion)
def filter_leadership_input(userQuestion: str, leaderShip: bool) -> str:
    """Sorun liderlikle alakalı ise bu tool, RAG sonuçlarını değerlendirir ve gerektiğinde web araması yapar."""
    rag_results = rag_tool.query(userQuestion, top_k=3)
    return evaluate_rag_results(userQuestion, rag_results)

# Rafine Edici Fonksiyon
def refine_with_model(input_data: Union[str, List[Dict]], memory: ConversationBufferMemory) -> str:
    input_text = format_rag_results(input_data) if isinstance(input_data, list) else input_data
    llm = ChatOpenAI(temperature=0.3)
    
    # Hafızadaki önceki mesajları ekleyerek bağlamı koru
    memory_messages = memory.chat_memory.messages
    messages = [
        SystemMessage(content=LEADERSHIP_COACH_SYSTEM_PROMPT),
        *memory_messages,
        HumanMessage(content=f"Bu bilgilere dayanarak nihai bir cevap ver (kısa ve öz olsun): {input_text}")
    ]
    
    result = llm(messages)
    return result.content if isinstance(result, AIMessage) else result

# Router Fonksiyonu
def route_result(result, memory: ConversationBufferMemory) -> str:
    tools = {"filter_leadership_input": filter_leadership_input}
    if isinstance(result, AgentFinish):
        return result.return_values['output']
    tool_output = tools[result.tool].run(result.tool_input)
    return refine_with_model(tool_output, memory)

# Agent ve Chat Kurulumu
class LeadershipChat:
    def __init__(self):
        self.memory = ConversationBufferMemory(return_messages=True)
        self.chain = self._setup_chain()

    def _setup_chain(self):
        functions = [format_tool_to_openai_function(filter_leadership_input)]
        model = ChatOpenAI(temperature=0).bind(functions=functions)
        prompt = ChatPromptTemplate.from_messages([
            ("system", LEADERSHIP_COACH_SYSTEM_PROMPT),
            ("placeholder", "{chat_history}"),
            ("user", "{input}")
        ])
        chain = (
            prompt
            | model
            | OpenAIFunctionsAgentOutputParser()
            | (lambda x: route_result(x, self.memory))
        )
        return chain

    def chat(self, user_input: str) -> str:
        # Hafızaya kullanıcı girdisini ekle
        self.memory.chat_memory.add_user_message(user_input)
        
        # Chain'i çalıştır ve sonucu al
        result = self.chain.invoke({
            "input": user_input,
            "chat_history": self.memory.chat_memory.messages[:-1]  # Son mesajı hariç tut (yeni input)
        })
        
        # Hafızaya AI cevabını ekle
        self.memory.chat_memory.add_ai_message(result)
        return result

