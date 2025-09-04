import os
import yt_dlp
import whisper
import colorama
import logging
from colorama import Fore, Style
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import Playlist
from tqdm import tqdm
from pathlib import Path

TRANSCRIPTIONS_DIR = "transcriptions"
AUDIO_FILES_DIR = "audio_files"

# Logging setup
SCRIPT_DIR = Path.cwd()
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "transcript_processing.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_transcript_api(video_id):
    """YouTube Transcript API kullanarak transkript al."""
    logger.info(Fore.CYAN + f"🔍 API ile transkript alınıyor: {video_id}" + Style.RESET_ALL)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['tr'])
        transcript_text = "\n".join([f"{entry['start']:.2f}s: {entry['text']}" for entry in transcript])
        logger.info(Fore.GREEN + f"✅ API ile transkript başarıyla alındı: {video_id}" + Style.RESET_ALL)
        return transcript_text
    except Exception as e:
        logger.warning(Fore.YELLOW + f"⚠️ API ile transkript alınamadı ({video_id}): {e}" + Style.RESET_ALL)
        return None

def download_audio(video_url, output_dir, index, video_id):
    """Videodan sesi indir ve MP3 olarak kaydet."""
    audio_file_path = f"{output_dir}/video_{index}_{video_id}.mp3"
    if os.path.exists(audio_file_path):
        logger.info(Fore.GREEN + f"✅ Ses dosyası zaten mevcut: {audio_file_path}" + Style.RESET_ALL)
        return audio_file_path, video_id

    logger.info(Fore.CYAN + f"⬇️ Ses dosyası indiriliyor: {video_url}" + Style.RESET_ALL)
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': audio_file_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            logger.info(Fore.GREEN + f"✅ Ses dosyası indirildi: {audio_file_path}" + Style.RESET_ALL)
            return audio_file_path, info['id']
    except Exception as e:
        logger.error(Fore.RED + f"❌ Ses indirme hatası ({video_url}): {e}" + Style.RESET_ALL)
        return None, None

def transcribe_audio(audio_file, output_dir, index, video_id):
    """Whisper modeli ile sesi metne çevir ve transkriptleri kaydet."""
    transcript_file = f"{TRANSCRIPTIONS_DIR}/transcript_{index}_{video_id}.txt"
    if os.path.exists(transcript_file):
        logger.info(Fore.GREEN + f"✅ Transkript dosyası zaten mevcut: {transcript_file}" + Style.RESET_ALL)
        return None

    logger.info(Fore.CYAN + f"🎙️ Ses dosyası transkribe ediliyor: {audio_file}" + Style.RESET_ALL)
    try:
        model = whisper.load_model("base")
        print(Fore.CYAN + "🎧 Transkripsiyon başlıyor, bu biraz zaman alabilir..." + Style.RESET_ALL)
        with tqdm(total=100, desc=Fore.MAGENTA + "🔊 Transkripsiyon ilerliyor" + Style.RESET_ALL, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}%") as pbar:
            result = model.transcribe(audio_file, language="tr")
            pbar.update(100)
        transcript_text = result["text"]

        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        logger.info(Fore.GREEN + f"✅ Transkript başarıyla kaydedildi: {transcript_file}" + Style.RESET_ALL)
        return transcript_text
    except Exception as e:
        logger.error(Fore.RED + f"❌ Transkripsiyon hatası ({audio_file}): {e}" + Style.RESET_ALL)
        return None

def process_playlist(playlist_url):
    """Playlist'teki videoları işle."""
    playlist = Playlist(playlist_url)
    os.makedirs(AUDIO_FILES_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)

    logger.info(Fore.CYAN + f"📜 Playlist işlenmeye başlıyor: {playlist_url}" + Style.RESET_ALL)
    for idx, video in enumerate(playlist.videos, start=1):
        video_id = video.video_id
        logger.info(Fore.CYAN + f"🔹 Video işleniyor: {idx} ({video_id})" + Style.RESET_ALL)

        audio_file = f"{AUDIO_FILES_DIR}/video_{idx}_{video_id}.mp3"
        transcript_file = f"{TRANSCRIPTIONS_DIR}/transcript_{idx}_{video_id}.txt"

        if os.path.exists(audio_file):
            logger.info(Fore.GREEN + f"✅ Video dosyası mevcut: {audio_file}" + Style.RESET_ALL)
        if os.path.exists(transcript_file):
            logger.info(Fore.GREEN + f"✅ Transkript mevcut: {transcript_file}" + Style.RESET_ALL)

        if os.path.exists(audio_file) and os.path.exists(transcript_file):
            logger.info(Fore.GREEN + f"✅ İşlem tamam: Ses ve transkript mevcut, video atlanıyor." + Style.RESET_ALL)
            continue

        transcript = get_transcript_api(video_id)

        if transcript and not os.path.exists(transcript_file):
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(transcript)
            logger.info(Fore.GREEN + f"✅ API ile transkript dosyası kaydedildi: {transcript_file}" + Style.RESET_ALL)
        else:
            if not os.path.exists(audio_file):
                audio_file, video_id = download_audio(video.watch_url, AUDIO_FILES_DIR, idx, video_id)
            if audio_file:
                transcript = transcribe_audio(audio_file, TRANSCRIPTIONS_DIR, idx, video_id)
            else:
                logger.error(Fore.RED + f"❌ Video işlenemedi: {video.watch_url}" + Style.RESET_ALL)

def main():
    colorama.init()
    PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLCi3Q_-uGtdlCsFXHLDDHBSLyq4BkQ6gZ"
    logger.info(Fore.CYAN + "🔹 İşlem başlıyor: API öncelikli, gerekirse indirme yapılacak." + Style.RESET_ALL)
    process_playlist(PLAYLIST_URL)
    logger.info(Fore.GREEN + "🎉 Tüm işlemler tamamlandı!" + Style.RESET_ALL)

if __name__ == "__main__":
    main()