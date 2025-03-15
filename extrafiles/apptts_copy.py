import os
from pathlib import Path
import logging
import streamlit as st
import requests
import tempfile

# Script’in çalıştığı dizini al ve logları yapılandır
SCRIPT_DIR = Path.cwd()  # Mevcut dizini al
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "leadership_coach.log"

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

# API ayarları
API_BASE_URL = "https://your-leadership-api-url.com"  # Replace with actual URL
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"
RESET_ENDPOINT = f"{API_BASE_URL}/reset"

def get_coach_response(prompt: str) -> tuple[str, str]:
    """API’den metin yanıtı alır ve OpenAI TTS ile ses oluşturur."""
    try:
        # API’den metin yanıtı al
        response = requests.post(CHAT_ENDPOINT, json={"message": prompt}, timeout=10)
        response.raise_for_status()
        coach_reply = response.json()["response"]
        logger.info(f"Kullanıcı sorgusu: '{prompt}' - Yanıt: '{coach_reply}'")

        # OpenAI TTS ile ses dosyası oluştur
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY eksik, ses dosyası oluşturulmayacak.")
            return coach_reply, None

        from openai import OpenAI
        openai_client = OpenAI(api_key=openai_api_key)
        audio_response = openai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",  # Ses seçeneği: alloy, echo, fable, onyx, nova, shimmer
            input=coach_reply
        )
        
        # Geçici ses dosyası kaydet
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            audio_response.stream_to_file(temp_audio.name)
            audio_path = temp_audio.name

        return coach_reply, audio_path
    except requests.RequestException as e:
        logger.error(f"API isteği başarısız: {e}")
        return "Üzgünüm, şu anda yanıt alamadım. Lütfen tekrar deneyin.", None
    except Exception as e:
        logger.error(f"Ses oluşturulurken hata: {e}")
        return coach_reply, None  # Metin yanıtı varsa onu döndür, ses yoksa None

def reset_chat():
    """API üzerinden hafızayı sıfırlar."""
    try:
        response = requests.get(RESET_ENDPOINT, timeout=5)
        response.raise_for_status()
        logger.info("Sohbet hafızası sıfırlandı.")
        return True
    except requests.RequestException as e:
        logger.error(f"Hafıza sıfırlama başarısız: {e}")
        return False

def main():
    """Streamlit UI ile Leadership Coach chatbot’unu çalıştırır."""
    # API’nin çalıştığını kontrol et (opsiyonel)
    try:
        requests.get(API_BASE_URL, timeout=5)
    except requests.RequestException:
        st.error("API bağlantısı kurulamadı. Lütfen API’nin çalıştığından emin olun.")
        logger.error("API bağlantısı başarısız.")
        return

    # Streamlit sayfa yapılandırması
    st.set_page_config(page_title="enocta.ai Leadership Coach", page_icon="🤝")
    st.title("🤝 enocta.ai Leadership Coach")
    st.caption("Liderlik becerilerinizi geliştirmek için AI destekli koçunuz!")

    # Sidebar
    with st.sidebar:
        st.markdown("""
        ### Hakkında
        Bu, **enocta.ai** tarafından geliştirilen bir AI liderlik koçudur. Sorular sorun, rehberlik alın ve liderlik potansiyelinizi keşfedin!
        
        - Sorular sorabilirsiniz: "Ekip motivasyonunu nasıl artırırım?"
        - Tavsiye isteyebilirsiniz: "Zor bir görüşme nasıl yönetilir?"
        
        **Not:** OPENAI_API_KEY ses desteği için gereklidir.
        """)
        st.write("© 2025 enocta.ai")

    # Sohbet geçmişi için session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Merhaba! Ben enocta.ai Leadership Coach. Sana liderlik yolculuğunda nasıl yardımcı olabilirim?"}
        ]

    # Sohbet mesajlarını göster
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "audio" in msg and msg["audio"]:
                st.audio(msg["audio"], format="audio/mp3")

    # Kullanıcı girdisi
    if prompt := st.chat_input("Sorunuzu veya talebinizi yazın..."):
        # Kullanıcı mesajını ekle ve göster
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Koçun yanıtını al ve göster
        with st.chat_message("assistant"):
            with st.spinner("Düşünüyorum..."):
                text_response, audio_path = get_coach_response(prompt)
            st.markdown(text_response)
            if audio_path:
                st.audio(audio_path, format="audio/mp3")
        st.session_state.messages.append({"role": "assistant", "content": text_response, "audio": audio_path})

    # Sohbeti Temizle butonu
    if st.button("Sohbeti Temizle"):
        if reset_chat():
            st.session_state.messages = [
                {"role": "assistant", "content": "Merhaba! Ben enocta.ai Leadership Coach. Sana liderlik yolculuğunda nasıl yardımcı olabilirim?"}
            ]
            st.success("Sohbet temizlendi!")
        else:
            st.error("Sohbet temizlenirken bir hata oluştu.")

if __name__ == "__main__":
    main()