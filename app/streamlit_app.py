import os
from pathlib import Path
import logging
import streamlit as st
import tempfile
from src.leadership_coach.agents.leadership import LeadershipChat

# Logging setup
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

# Initialize LeadershipChat
chat_instance = LeadershipChat()

def get_coach_response(prompt: str) -> tuple[str, str]:
    try:
        coach_reply = chat_instance.chat(prompt)
        logger.info(f"Kullanıcı sorgusu: '{prompt}' - \n Yanıt: '{coach_reply}'")

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY eksik, ses dosyası oluşturulmayacak.")
            return coach_reply, None

        from openai import OpenAI
        openai_client = OpenAI(api_key=openai_api_key)
        audio_response = openai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=coach_reply
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            audio_response.stream_to_file(temp_audio.name)
            audio_path = temp_audio.name

        return coach_reply, audio_path
    except Exception as e:
        logger.error(f"Yanıt oluşturulurken hata: {e}")
        return "Üzgünüm, şu anda yanıt veremiyorum. Lütfen tekrar deneyin.", None

def main():
    st.set_page_config(page_title="enocta.ai Leadership Coach", page_icon="🤝")
    st.title("🤝 enocta.ai Leadership Coach")
    st.caption("Liderlik becerilerinizi geliştirmek için AI destekli koçunuz!")

    with st.sidebar:
        st.sidebar.markdown("""
        ### Hakkında
        Bu, **enocta.ai** tarafından geliştirilen bir AI liderlik koçudur. Sorular sorun, rehberlik alın ve liderlik potansiyelinizi keşfedin!
        
        - Sorular sorabilirsiniz: "Ekip motivasyonunu nasıl artırırım?"
        - Tavsiye isteyebilirsiniz: "Zor bir görüşme nasıl yönetilir?"
        
        **Not:** Bot'u kullanırken Sağ Alt köşede bulunan Manage App'i tıklayarak, Data'nın RAG dan mı WEB ten mi geldiğini görebilirsiniz.
        """)
        st.write("© 2025 enocta.ai")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Merhaba! Ben enocta.ai Leadership Coach. Sana liderlik yolculuğunda nasıl yardımcı olabilirim?"}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "audio" in msg and msg["audio"]:
                st.audio(msg["audio"], format="audio/mp3")

    if prompt := st.chat_input("Sorunuzu veya talebinizi yazın..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Düşünüyorum..."):
                text_response, audio_path = get_coach_response(prompt)
            st.markdown(text_response)
            if audio_path:
                st.audio(audio_path, format="audio/mp3")
        st.session_state.messages.append({"role": "assistant", "content": text_response, "audio": audio_path})

    if st.button("Sohbeti Temizle"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Merhaba! Ben enocta.ai Leadership Coach. Sana liderlik yolculuğunda nasıl yardımcı olabilirim?"}
        ]
        st.success("Sohbet temizlendi!")

if __name__ == "__main__":
    main()
