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

# Logging konfigurasyonu
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"
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

# Transkript ve çıktı dizinleri
TRANSCRIPTIONS_DIR = Path("cleaned_transcriptions/")  # Transkript dosyalarının olduğu klasör
OUTPUT_FILE = SCRIPT_DIR / "rag_qa_data.json"

# GPT-4 ile LangChain yapılandırması
try:
    llm = ChatOpenAI(model_name="gpt-4", temperature=0.7, api_key=os.getenv("OPENAI_API_KEY"))
    prompt_template = PromptTemplate(
        input_variables=["transcript", "filename"],
        template="""
        Sen bir Liderlik Koçusun. Görevin, verilen transkriptten liderlik, yönetim veya kişisel gelişimle ilgili 
        10-15 adet doğal ve transkripte özgü soru çıkarmak ve bu sorulara transkriptteki bilgilere dayanarak 
        ilham verici, rehber ve yapılandırıcı yanıtlar üretmek. Tonun samimi ama profesyonel olsun; 
        kullanıcıyı motive et ve pratik öneriler sun. Şu adımları izle:
        1. Transkripti dikkatlice oku: {transcript}
        2. Transkriptteki liderlik temalarını (motivasyon, ekip yönetimi, risk alma, şeffaflık, vb.) tespit et.
        3. Her tema için transkripte özgü 3-5 soru oluştur (örneğin, "Ayşen Esen gibi bir lider zorlukları nasıl aşar?").
        4. Her soruya, transkriptten alıntı veya bilgiye dayanarak cevap ver. Cevap, koçluk tarzında olsun ve 
           pratik bir öneri içersin.
        5. Çıktıyı şu formatta JSON olarak ver:
           [
             {{
               "question": "Soru metni",
               "answer": "Cevap metni",
               "source": "{filename}",
               "speaker": "Konuşmacı adı (bilinmiyorsa Bilinmeyen Konuk)"
             }},
             ...
           ]
        """
    )
    chain = RunnableSequence(prompt_template | llm)
except Exception as e:
    logger.error(f"LLM veya chain başlatılamadı: {e}")
    chain = None

async def extract_qa_pairs(transcript_text: str, filename: str) -> List[dict]:
    """Transkriptten soru-cevap çiftlerini çıkar."""
    if not chain:
        logger.error("RunnableSequence başlatılmadı.")
        return []

    try:
        logger.info(f"{filename} için soru-cevap çiftleri çıkarılıyor...")
        # LangChain ile GPT-4'ü çalıştır
        result = await asyncio.to_thread(chain.invoke, {"transcript": transcript_text, "filename": filename})
        qa_pairs = json.loads(result.content.strip())  # GPT-4'ün JSON çıktısını parse et
        return qa_pairs
    except json.JSONDecodeError:
        logger.error(f"{filename} için JSON parse hatası. Ham çıktı: {result.content}")
        return []
    except Exception as e:
        logger.error(f"{filename} işlenirken hata: {e}")
        return []

async def process_transcript(file_path: Path) -> List[dict]:
    """Bir transkript dosyasını oku ve soru-cevap çiftlerini çıkar."""
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            transcript_text = await f.read()
    except Exception as e:
        logger.error(f"Dosya okunamadı {file_path}: {e}")
        return []

    filename = file_path.name
    qa_pairs = await extract_qa_pairs(transcript_text, filename)
    return qa_pairs

async def process_all_transcripts() -> None:
    """Tüm transkriptleri eşzamanlı olarak işle ve sonuçları kaydet."""
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

    # JSON dosyasına kaydet
    async with aiofiles.open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        await f.write(json.dumps(all_qa_pairs, ensure_ascii=False, indent=4))
    logger.info(f"Toplam {len(all_qa_pairs)} soru-cevap çifti {OUTPUT_FILE}'a kaydedildi.")

def main() -> None:
    """Ana giriş noktası."""
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY çevre değişkeni ayarlanmadı. Lütfen ayarlayın.")
        return

    logger.info("Transkriptlerden soru-cevap çiftleri çıkarılıyor...")
    asyncio.run(process_all_transcripts())

if __name__ == "__main__":
    main()