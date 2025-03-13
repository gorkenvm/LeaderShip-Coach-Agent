import os
import asyncio
from pathlib import Path
import logging
from tavily import TavilyClient

# Script’in çalıştığı dizini al ve logları yapılandır
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "tavily_search.log"

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Tavily istemcisini başlat
try:
    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
except Exception as e:
    logger.error(f"Tavily istemcisi başlatılamadı: {e}")
    tavily_client = None

async def search_web(query: str) -> dict:
    """Tavily ile web araması yapar ve sonucu döndürür."""
    if not tavily_client:
        logger.error("Tavily istemcisi mevcut değil.")
        return {"error": "Tavily istemcisi başlatılamadı."}

    try:
        # Tavily aramasını async bir şekilde çalıştır
        response = await asyncio.to_thread(
            tavily_client.search,
            query=query,
            max_results=5  # Maksimum 5 sonuç döndür
        )
        logger.info(f"Arama tamamlandı: '{query}'")
        return response
    except Exception as e:
        logger.error(f"Arama sırasında hata: {e}")
        return {"error": str(e)}

async def main():
    """Ana fonksiyon: Örnek bir arama yapar ve sonucu loglar."""
    if not os.getenv("TAVILY_API_KEY"):
        logger.error("TAVILY_API_KEY ortam değişkeni tanımlı değil.")
        return

    query = "Python ile yapay zeka projeleri"
    logger.info(f"Web araması başlatılıyor: '{query}'")
    result = await search_web(query)

    if "error" not in result:
        logger.info("Arama sonuçları:")
        for i, item in enumerate(result.get("results", []), 1):
            logger.info(f"{i}. {item['title']} - {item['url']}")
    else:
        logger.error(f"Sonuç alınamadı: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())