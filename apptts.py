import os
import asyncio
from pathlib import Path
import logging
import streamlit as st
from openai import OpenAI
import tempfile

# Script’in çalıştığı dizini al ve logları yapılandır
SCRIPT_DIR = Path(__file__).parent
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

# OpenAI istemcisini başlat
try:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    logger.error(f"OpenAI istemcisi başlatılamadı: {e}")
    openai_client = None

async def get_coach_response(prompt: str) -> tuple[str, str]:
    """Leadership Coach’un kullanıcı girdisine metin ve sesli yanıt vermesini sağlar."""
    if not openai_client:
        logger.error("OpenAI istemcisi mevcut değil.")
        return "Üzgünüm, şu anda size yardımcı olamıyorum.", None

    try:
        # Metin yanıtı al
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sen bir liderlik koçusun ve enocta.ai tarafından geliştirildin. Kullanıcılara profesyonel, rehber ve ilham verici yanıtlar ver."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        coach_reply = response.choices[0].message.content.strip()
        logger.info(f"Kullanıcı sorgusu: '{prompt}' - Yanıt: '{coach_reply}'")

        # TTS ile ses dosyası oluştur
        audio_response = await asyncio.to_thread(
            openai_client.audio.speech.create,
            model="tts-1",
            voice="alloy",  # Ses seçeneği: alloy, echo, fable, onyx, nova, shimmer
            input=coach_reply
        )
        # Geçici ses dosyası kaydet
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            audio_response.stream_to_file(temp_audio.name)
            audio_path = temp_audio.name

        return coach_reply, audio_path
    except Exception as e:
        logger.error(f"Yanıt alınırken hata: {e}")
        return "Bir hata oluştu, lütfen tekrar deneyin.", None

def main():
    """Streamlit UI ile Leadership Coach chatbot’unu çalıştırır."""
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY ortam değişkeni tanımlı değil.")
        st.error("Lütfen OPENAI_API_KEY ortam değişkenini tanımlayın.")
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
        
        **Not:** OPENAI_API_KEY gereklidir.
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
                text_response, audio_path = asyncio.run(get_coach_response(prompt))
            st.markdown(text_response)
            if audio_path:
                st.audio(audio_path, format="audio/mp3")
                # Geçici dosyayı geçmişe eklemeden önce temizleme yapabiliriz, ama burada tutuyoruz
        st.session_state.messages.append({"role": "assistant", "content": text_response, "audio": audio_path})

if __name__ == "__main__":
    main()