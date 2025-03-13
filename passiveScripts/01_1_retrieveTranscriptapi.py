import os
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import Playlist
from pathlib import Path

# Sabitler
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLCi3Q_-uGtdlCsFXHLDDHBSLyq4BkQ6gZ"
TRANSCRIPTIONS_DIR = "transcriptions"

def get_transcript(video_id):
    """YouTube Transcript API ile transkript al, hata varsa None döndür."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['tr'])
        return "\n".join([f"{entry['start']:.2f}s: {entry['text']}" for entry in transcript])
    except Exception as e:
        print(f"Hata (Video ID: {video_id}): {e}")
        return None

def save_transcript(video_id, transcript, index):
    """Transkripti dosyaya kaydet."""
    # Klasörü oluştur
    Path(TRANSCRIPTIONS_DIR).mkdir(parents=True, exist_ok=True)
    
    transcript_file = f"{TRANSCRIPTIONS_DIR}/transcript_{index}_{video_id}.txt"
    
    # Dosya zaten varsa kaydetmeyi atla
    if os.path.exists(transcript_file):
        print(f"✅ Transkript zaten mevcut, atlanıyor: {transcript_file}")
        return
    
    # Transkripti kaydet
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(transcript)
    print(f"✅ Transkript kaydedildi: {transcript_file}")

def process_playlist(playlist_url):
    """Playlist'teki videoları işle."""
    # Playlist'teki video ID'lerini al
    playlist = Playlist(playlist_url)
    video_ids = [video.video_id for video in playlist.videos]

    # Her bir video için transkript al ve kaydet
    for idx, video_id in enumerate(video_ids, start=1):
        print(f"\n=== İşleniyor: Video {idx} (ID: {video_id}) ===")
        
        # Transkripti al
        transcript = get_transcript(video_id)
        
        # Transkript varsa kaydet, yoksa hiçbir şey yapma
        if transcript:
            save_transcript(video_id, transcript, idx)
        else:
            print(f"⚠️ Transkript alınamadı, dosya kaydedilmeyecek.")

def main():
    print("🔹 Transkript alma işlemi başlıyor...")
    process_playlist(PLAYLIST_URL)
    print("🎉 İşlem tamamlandı!")

if __name__ == "__main__":
    main()