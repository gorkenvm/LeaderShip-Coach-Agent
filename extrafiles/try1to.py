from langchain.agents import tool
from pydantic import BaseModel, Field
from typing import List, Dict,Union
import requests
import json
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableMap
from langchain.agents import AgentExecutor
import os
import openai
from RagClass import RagTool, WebSearchTool
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
openai.api_key = os.environ['OPENAI_API_KEY']
from langchain.agents import tool
from collections import Counter

rag_tool = RagTool()
web_search_tool = WebSearchTool()

def evaluate_rag_results_with_llm(user_question: str, rag_results: List[Dict]) -> bool:
    """
    LLM kullanarak RAG sonuçlarının kullanıcı sorusuna uygunluğunu değerlendirir.
    """
    if not rag_results or len(rag_results) == 0:
        return False

    # LLM örneği (örneğin OpenAI, senin modelinle değiştirilebilir)
    llm = ChatOpenAI( temperature=0.3) 

    # Prompt template: LLM'ye soruyu ve RAG sonuçlarını gönderiyoruz
    eval_prompt = ChatPromptTemplate.from_messages([
        ("system", """
            Sen bir değerlendirme asistanısın. Görevin, verilen kullanıcı sorusuna RAG sonuçlarının uygun, doğru ve yeterli olup olmadığını kontrol etmek.
            Kriterler:
            - RAG'daki sorular ve cevaplar, kullanıcı sorusuyla anlamsal olarak uyumlu olmalı.
            - Cevaplar yeterli bilgi içermeli (çok kısa veya alakasız olmamalı).
            Çıktı olarak yalnızca 'True' veya 'False' döndür, başka açıklama ekleme.
        """),
        ("user", """
            Kullanıcı sorusu: {user_question}
            RAG sonuçları: {rag_results}
        """)
    ])

    # RAG sonuçlarını string formatına çevir (LLM için)
    rag_results_str = "\n".join([f"Soru: {r['question']}\nCevap: {r['answer']}" for r in rag_results])

    # LLM sorgusu
    response = llm(eval_prompt.format_messages(user_question=user_question, rag_results=rag_results_str))
    
    if response.content.strip() == "True":
        print("RAG sonuçları yeterli ve doğru.")
        return rag_results_str
    else :
        print("RAG sonuçları yetersiz veya yanlış.")
        try:
            results = web_search_tool.search(
            query=user_question,
            max_results=3,
            include_answer="advanced",
            include_images=False,
            include_image_descriptions=False,
            search_depth="advanced"
                                    )
            web_results_str = "\n".join([f"Başlık: {r['title']}\nURL: {r['url']}\nÖzet: {r['snippet']}" for r in results['results']])
            return web_results_str
        except:
            print("Web araması yapılamadı.")
            return rag_results_str

class userQuestion(BaseModel):
    userQuestion: str = Field(description="Kullanıcının sorduğu soru", example="Nasıl lider olunur?")
    leaderShip: bool = Field(description="Sorunun Liderlikle alakalı olup olmadığını belirler.", example="True")


@tool(args_schema=userQuestion)
def FilterLeaderShipInput( userQuestion: str,leaderShip: bool) -> str:
    """Kullanıcı sorusu liderlik ile ilgili ise RAG metodu ile fetch edilir. """
    rag_results = rag_tool.query(userQuestion, top_k=3)
    result = evaluate_rag_results_with_llm(userQuestion, rag_results)
        
    return result



from langchain.tools.render import format_tool_to_openai_function


functions = [
    format_tool_to_openai_function(f) for f in [
        FilterLeaderShipInput
    ]
]
model = ChatOpenAI(temperature=0).bind(functions=functions)


from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(return_messages=True)

from langchain.prompts import ChatPromptTemplate
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser

prompt = ChatPromptTemplate.from_messages([
    ("system", """
        Sen bir liderlik koçusun ve amacın kullanıcılara rehberlik etmek, ilham vermek ve stratejik düşünmelerine yardımcı olmak. 
        Tonun profesyonel, empatik ve ilham verici olmalı. 
        Cevaplarını, doğal, yapılandırılmış ve içgörü sunan bir şekilde ver. 
        Kullanıcıya bir koç gibi yaklaş, sorularını dikkatle analiz et ve gerektiğinde yönlendirici sorularla derinleştir.
        Kullanıcı liderlik ile ilgili bir soru sormuyorsa soruyu anlamaya çalış ve gerektiğinde kullanıcıyı yönlendir.
        Cevaplarında somut örnekler ve rehber ilkeler sunmaya özen göster. 
    """),
    ("user", "{input}")
])

from langchain.schema.agent import AgentFinish
from langchain_core.messages import AIMessage

def refine_with_model(input_data: Union[str, list]) -> str:
    """
    route'dan gelen sonucu modele geri besler ve son cevabı üretir.
    """
    # Gelen input'un string olduğundan emin olalım (liste ise birleştir)
    if isinstance(input_data, list):
        input_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in input_data])
    else:
        input_text = input_data
    

    # Modeli tekrar çağırarak sonucu rafine et
    refined_prompt = f"""Sen bir liderlik koçusun ve amacın kullanıcılara rehberlik etmek, ilham vermek ve stratejik düşünmelerine yardımcı olmak. 
        Tonun profesyonel, empatik ve ilham verici olmalı. 
        Cevaplarını, doğal, yapılandırılmış ve içgörü sunan bir şekilde ver.  
        Bu bilgilere kullanarak nihai bir cevap ver ancak cevap uzun olmasın, ayrıca sağlanan bilgilerden en alakalı olanları kullan: {input_text}
        
        Örnek 1 : Finans sektöründe yaşanan krizler, kurumsal yapının ve çalışanların hızlı adapte olmasını zorunlu kılıyor. Konuşmada banka deneyimleri üzerinden, kriz anlarında doğru karar almanın ve stratejik değişimin önemine vurgu yapılıyor.
        
        Örnek 2 : Mentorluk sürecinde, deneyimlerimi paylaşmak ve sürekli öğrenme kültürünü desteklemek anahtar rol oynuyor. Risk alma, eleştiriye açık olma ve sürekli gelişim, başarılı bir mentorluğun temel unsurlarıdır.Zz
       
        """
    llm = ChatOpenAI( temperature=0.3)
    refined_result = llm(refined_prompt)
    if isinstance(refined_result, AIMessage):
        return refined_result.content

    return refined_result


def route(result):
    if isinstance(result, AgentFinish):
        
        return result.return_values['output']
    else:
        tools = {
            "FilterLeaderShipInput": FilterLeaderShipInput, 
        }
        return refine_with_model(input_data = tools[result.tool].run(result.tool_input))


chain = prompt | model | OpenAIFunctionsAgentOutputParser() | route 


result = chain.invoke({"input": "Kriz zamanlarında lider olarak nasıl stratejiler geliştiriyorsunuz?"})
print(result)