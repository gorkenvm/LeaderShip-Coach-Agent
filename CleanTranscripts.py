import os
import asyncio
from pathlib import Path
from typing import List, Tuple
import logging

import aiofiles
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Logging configuration
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)  # Log dizinini oluştur
LOG_FILE = LOG_DIR / "transcript_processing.log"

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),  # Dosyaya yaz
        logging.StreamHandler()  # Konsola yaz
    ]
)
logger = logging.getLogger(__name__)

# Directories
TRANSCRIPTIONS_DIR = Path(r"C:\Users\veysel_gorken\Desktop\enocta-ai\transcriptions")
CLEANED_DIR = Path(r"C:\Users\veysel_gorken\Desktop\enocta-ai\cleaned_transcriptions")

# Ensure cleaned directory exists
CLEANED_DIR.mkdir(parents=True, exist_ok=True)

# Initialize LLM and prompt globally
try:
    llm = ChatOpenAI(model_name="gpt-4", temperature=0.7)
    prompt_template = PromptTemplate(
        input_variables=["transcript_text"],
        template=(
            "Aşağıdaki transkript bir TV programından alınmıştır. Programda bir Sunucu ve bir Konuk vardır. "
            "Sunucu genelde sorular sorar, Konuk ise yanıtlar verir. Görevin şu adımları takip etmek:\n"
            "1. Metni temizle: Yanlış yazımları düzelt (örneğin 'saykıl' yerine 'sirküle'), dolgu ifadeleri "
            "(örneğin 'eee', 'hani', 'şey') ve tekrarlamaları kaldır, cümle düşüklüklerini düzelt, programla "
            "alakasız ifadeleri (örneğin 'abone ol') çıkar.\n"
            "2. Konuşmacıları ayır: Her konuşmayı 'Time: [süre] Sunucu: ...' veya 'Time: [süre] Konuk: ...' "
            "formatında bir liste olarak döndür. Konuşmacıları ayırırken, bağlama göre kimin konuştuğunu mantıklı "
            "bir şekilde belirle.\n"
            "3. Metni doğal ve akıcı bir hale getir.\n"
            "4. Süre bilgisi: Eğer transkriptte süreler verilmişse (örneğin '0.08s:'), bu süreleri konuşmaların "
            "başına ekle. Eğer süre bilgisi yoksa, yaklaşık 22 dakikalık (1320 saniye) bir video varsayımıyla, "
            "her satır için tahmini bir süre hesapla ve ekle.\n\n"

            "Metin: {transcript_text}\n\n"
            "Temizlenmiş ve ayrılmış hali:"
        )
    )
    chain = RunnableSequence(prompt_template | llm)
except Exception as e:
    logger.error(f"Failed to initialize LLM or chain: {e}")
    chain = None

# Text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=4000,
    chunk_overlap=200
)

async def clean_and_split_with_llm(transcript_text: str) -> List[Tuple[str, str]]:
    """Clean and split transcript text using LLM asynchronously."""
    if not chain:
        logger.error("RunnableSequence is not initialized.")
        return []

    try:
        chunks = text_splitter.split_text(transcript_text)
        cleaned_lines: List[Tuple[str, str]] = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
            # Use invoke instead of run for RunnableSequence
            result = await asyncio.to_thread(chain.invoke, {"transcript_text": chunk})
            cleaned_text = result.content.strip()  # Access content from ChatOpenAI response

            for line in cleaned_text.split("\n"):
                line = line.strip() 
                # Time bilgisini ayıklıyoruz
                if "Time:" in line:
                    time_part = line.split("Time:")[1].split("s")[0].strip()
                
                if line.startswith("Sunucu:"):
                    speaker, text = "Sunucu", line.replace("Sunucu:", "").strip()
                elif line.startswith("Konuk:"):
                    speaker, text = "Konuk", line.replace("Konuk:", "").strip()
                else:
                    continue

                # Time bilgisini de ekliyoruz
                if text:
                    cleaned_lines.append((speaker, text, time_part))

        return cleaned_lines
    except Exception as e:
        logger.error(f"Error during LLM processing: {e}")
        return []

async def save_cleaned_transcript(cleaned_lines: List[Tuple[str, str]], output_path: Path) -> None:
    """Save cleaned transcript to file asynchronously."""
    if not cleaned_lines:
        logger.warning(f"No cleaned content for {output_path}, saving empty file.")

    async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
        for speaker, text in cleaned_lines:
            await f.write(f"{speaker}: {text}\n")

async def clean_and_structure_transcript(input_path: Path, output_path: Path) -> None:
    """Read, clean, and structure a transcript file asynchronously."""
    try:
        async with aiofiles.open(input_path, "r", encoding="utf-8") as f:
            transcript_text = await f.read()
    except Exception as e:
        logger.error(f"Error reading file {input_path}: {e}")
        return

    cleaned_lines = await clean_and_split_with_llm(transcript_text)
    await save_cleaned_transcript(cleaned_lines, output_path)
    logger.info(f"Cleaned file saved: {output_path}")

async def process_all_transcripts() -> None:
    """Process all transcript files in the directory concurrently."""
    if not TRANSCRIPTIONS_DIR.exists():
        logger.error(f"Directory not found: {TRANSCRIPTIONS_DIR}")
        return

    tasks = []
    for file_path in TRANSCRIPTIONS_DIR.glob("*.txt"):
        output_path = CLEANED_DIR / file_path.name
        tasks.append(clean_and_structure_transcript(file_path, output_path))

    if tasks:
        await asyncio.gather(*tasks)
    else:
        logger.warning("No .txt files found in the transcriptions directory.")

def main() -> None:
    """Main entry point to run the async script."""
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set. Please set it before running.")
        return

    logger.info("Starting transcript cleaning and structuring with LangChain and LLM...")
    asyncio.run(process_all_transcripts())

if __name__ == "__main__":
    main()