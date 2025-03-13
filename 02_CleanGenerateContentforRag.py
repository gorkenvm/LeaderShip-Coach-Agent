import os
import asyncio
from pathlib import Path
from typing import List
import json
import logging

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
import aiofiles


SCRIPT_DIR = Path.cwd()  # Mevcut dizini al
LOG_DIR = SCRIPT_DIR / "logs"
OUTPUT_FILE = SCRIPT_DIR / "rag_qa_data.json"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "qa_extraction.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Dizinler
TRANSCRIPTIONS_DIR = Path("transcriptions/")
OUTPUT_FILE = SCRIPT_DIR / "rag_qa_data.json"

# Boş JSON dosyası oluştur
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump([], f, ensure_ascii=False, indent=2)
print(f"{OUTPUT_FILE} başarıyla oluşturuldu.")

# GPT-4 ve LangChain yapılandırması
try:
    llm = ChatOpenAI(model_name="o3-mini", api_key=os.getenv("OPENAI_API_KEY"))
    prompt_template = PromptTemplate(
        input_variables=["transcript", "filename"],
        template=(
            "Aşağıdaki transkript bir TV programından alınmıştır ve bir Sunucu ile bir Konuk arasında geçen konuşmayı içerir. "
            "Sunucu genelde sorular sorar, Konuk ise yanıtlar verir. Görevin iki aşamalıdır:\n\n"

            "### Aşama 1: Transkripti Temizle ve Konuşmacıları Ayır\n"
            "1. Metni temizle: Yanlış yazımları düzelt, dolgu ifadeleri ve alakasız kısımları çıkar.\n"
            "2. Konuşmacıları ayır: Her konuşmayı 'Time: [süre] Sunucu: ...' veya 'Time: [süre] Konuk: ...' formatında bir liste olarak hazırla.\n"
            "3. Süre bilgisi: Transkriptte süre varsa kullan, yoksa tahmini süre ekle.\n\n"

            "### Aşama 2: Liderlik Koçluğu Soruları ve Yanıtları Üret\n"
            "Temizlenmiş transkripti kullanarak:\n"
            "1. Liderlik temalarını tespit et.\n"
            "2. 13-15 doğal ve ilham verici soru oluştur.\n"
            "3. Her soruya transkriptten alıntıya dayalı rehber cevaplar ver.\n"
            "4. Çıktıyı yalnızca aşağıdaki JSON formatında döndür (başka metin ekleme):\n"
            "   [\n"
            "     {{\n"
            "       \"question\": \"Soru metni\",\n"
            "       \"answer\": \"Cevap metni\",\n"
            "       \"source\": \"{filename}\",\n"
            "       \"speaker\": \"Konuşmacı adı (bilinmiyorsa Bilinmeyen Konuk)\",\n"
            "       \"time\": \"[süre in second format as 1049 or 542]\"\n" 
            "     }},\n"
            "     ...\n"
            "   ]\n\n"

            "Metin: {transcript}\n\n"
            "Aşama 1 in çıktısına ihtiyacım yok Yalnızca aşama 2 nin çıktısını JSON formatında çıktı ver, başka açıklama veya metin ekleme."
        )
    )
    chain = RunnableSequence(prompt_template | llm)
except Exception as e:
    logger.error(f"LLM veya chain başlatılamadı: {e}")
    chain = None

async def extract_qa_pairs(transcript_text: str, filename: str) -> List[dict]:
    if not chain:
        logger.error("RunnableSequence başlatılmadı.")
        return []

    try:
        logger.info(f"{filename} için soru-cevap çiftleri çıkarılıyor...")
        result = await asyncio.to_thread(chain.invoke, {"transcript": transcript_text, "filename": filename})
        logger.debug(f"{filename} için ham çıktı: {result.content}")
        qa_pairs = json.loads(result.content.strip())
        return qa_pairs
    except json.JSONDecodeError as e:
        logger.error(f"{filename} için JSON parse hatası: {e}. Ham çıktı: {result.content}")
        with open(f"error_output_{filename}.txt", "w", encoding="utf-8") as f:
            f.write(result.content)
        return []
    except Exception as e:
        logger.error(f"{filename} işlenirken hata: {e}")
        return []

async def process_transcript(file_path: Path) -> List[dict]:
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            transcript_text = await f.read()
        if not transcript_text.strip():
            logger.warning(f"{file_path} boş bir dosya.")
            return []
        filename = file_path.name
        qa_pairs = await extract_qa_pairs(transcript_text, filename)
        return qa_pairs
    except Exception as e:
        logger.error(f"Dosya okunamadı {file_path}: {e}")
        return []

async def process_all_transcripts() -> None:
    if not TRANSCRIPTIONS_DIR.exists():
        logger.error(f"Dizin bulunamadı: {TRANSCRIPTIONS_DIR}")
        return

    all_qa_pairs = []
    tasks = []

    for file_path in TRANSCRIPTIONS_DIR.glob("*.txt"):
        tasks.append(process_transcript(file_path))

    if tasks:
        results = await asyncio.gather(*tasks)
        for qa_pairs in results:
            all_qa_pairs.extend(qa_pairs)
            logger.info(f"{len(qa_pairs)} soru-cevap çifti eklendi.")

    async with aiofiles.open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        await f.write(json.dumps(all_qa_pairs, ensure_ascii=False, indent=4))
    logger.info(f"Toplam {len(all_qa_pairs)} soru-cevap çifti {OUTPUT_FILE}'a kaydedildi.")

def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY çevre değişkeni ayarlanmadı. Lütfen ayarlayın.")
        return

    logger.info("Transkriptlerden soru-cevap çiftleri çıkarılıyor...")
    asyncio.run(process_all_transcripts())

if __name__ == "__main__":
    main()