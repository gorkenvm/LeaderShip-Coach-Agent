import os
import yt_dlp
from pytube import Playlist
import whisper
import argparse

# Playlist URL'si
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLCi3Q_-uGtdlCsFXHLDDHBSLyq4BkQ6gZ"

# Ses dosyalarının ve transkripsiyonların kaydedileceği dizinler
OUTPUT_DIR = "audio_files"
TRANSCRIPTIONS_DIR = "transcriptions"

# Dizinleri oluştur
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)


model = whisper.load_model("base", device="cpu") # "small", "medium", "large" seçenekleri de var


def download_audio(video_url, output_dir, index, format="mp3"):
    """
    Tek bir videoyu MP3 formatında indirir.
    format: Varsayılan olarak "mp3"
    index: Dosya adında sıralama için kullanılacak
    """
    try:
        # Önce video ID'yi çıkar
        info = None
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
        video_id = info['id']
        
        # Ses dosyasının hedef yolunu oluştur
        output_file = f"{output_dir}/video_{index}_{video_id}.{format}"
        
        # Eğer ses dosyası zaten varsa indirme yapma
        if os.path.exists(output_file):
            print(f"Ses dosyası zaten mevcut, indirme atlanıyor: {output_file}")
            return output_file

        # İndirme seçeneklerini ayarla
        ydl_opts = {
            'format': 'bestaudio/best',  # En iyi ses kalitesini seç
            'outtmpl': f'{output_dir}/video_{index}_%(id)s.%(ext)s',  # Dosya adı formatı
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',  # Ses dosyasını MP3'e çevir
                'preferredcodec': format,
                'preferredquality': '320',  # 320 kbps MP3
            }],
            'quiet': False,
            'no_warnings': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Video {index} indiriliyor: {video_url}")
            ydl.download([video_url])
            print(f"Ses dosyası kaydedildi: {output_file}")
            return output_file
    except Exception as e:
        print(f"Video {index} indirilirken hata oluştu ({video_url}): {e}")
        return None

def transcribe_audio(audio_file_path, output_dir, index, video_id):
    """
    Ses dosyasını metne çevirir ve transkripsiyonu kaydeder.
    """
    # Transkripsiyon dosyasının hedef yolu
    transcript_file_path = f"{output_dir}/transcript_{index}_{video_id}.txt"
    
    # Eğer transkripsiyon dosyası zaten varsa atla
    if os.path.exists(transcript_file_path):
        print(f"Transkripsiyon dosyası zaten mevcut, transkripsiyon atlanıyor: {transcript_file_path}")
        return None

    try:
        print(f"Ses dosyası transkripsiyona çevriliyor: {audio_file_path}")
        model = whisper.load_model("base")  # "small", "medium", "large" seçenekleri de var
        result = model.transcribe(audio_file_path, language="tr")  # Türkçe için dil belirttim
        transcript_text = result["text"]

        # Transkripsiyonu dosyaya kaydet
        with open(transcript_file_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        print(f"Transkripsiyon başarıyla kaydedildi: {transcript_file_path}")
        return transcript_text
    except Exception as e:
        print(f"Transkripsiyon sırasında hata oluştu ({audio_file_path}): {e}")
        return None

def process_playlist(playlist_url, audio_output_dir, transcript_output_dir, mode, audio_format="mp3"):
    """
    Playlist'teki tüm videoları işler: indirme ve/veya transkripsiyon.
    mode: "download", "transcribe", "both"
    audio_format: Varsayılan olarak "mp3"
    """
    try:
        # Playlist'i yükle
        playlist = Playlist(playlist_url)
        print(f"Playlist Başlığı: {playlist.title}")
        print(f"Toplam Video Sayısı: {len(playlist.video_urls)}")

        # Her bir video için işlem yap
        for idx, video_url in enumerate(playlist.video_urls, start=1):
            print(f"\nİşleniyor: Video {idx}/{len(playlist.video_urls)}")

            # Video ID'yi çıkar
            info = None
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
            video_id = info['id']
            audio_file = f"{audio_output_dir}/video_{idx}_{video_id}.{audio_format}"

            # Mode'a göre işlem yap
            if mode in ["download", "both"]:
                # Ses dosyasını indir (veya varsa atla)
                audio_file = download_audio(video_url, audio_output_dir, idx, audio_format)
                if not audio_file:
                    continue  # Eğer ses dosyası indirilemediyse bir sonraki videoya geç
            else:
                # Sadece transkripsiyon modundaysa ses dosyasını kontrol et
                if not os.path.exists(audio_file):
                    print(f"Ses dosyası bulunamadı, transkripsiyon için dosya gerekli: {audio_file}")
                    continue

            if mode in ["transcribe", "both"]:
                # Ses dosyasını metne çevir (veya varsa atla)
                transcribe_audio(audio_file, transcript_output_dir, idx, video_id)

    except Exception as e:
        print(f"Playlist işlenirken hata oluştu: {e}")

def main():
    # Komut satırı argümanlarını işle
    parser = argparse.ArgumentParser(description="YouTube Playlist İşleme Script’i")
    parser.add_argument('--mode', type=str, choices=['download', 'transcribe', 'both'], 
                        help='İşlem modu: download (sadece indirme), transcribe (sadece transkripsiyon), both (her ikisi)')
    args = parser.parse_args()

    # Eğer argüman verilmediyse kullanıcıya sor
    if not args.mode:
        print("Ne yapmak istediğinizi seçin:")
        print("1. Sadece videoları indir (download)")
        print("2. Sadece transkripsiyon yap (transcribe)")
        print("3. Her ikisini yap (both)")
        choice = input("Seçiminiz (1/2/3): ").strip()
        
        if choice == "1":
            mode = "download"
        elif choice == "2":
            mode = "transcribe"
        elif choice == "3":
            mode = "both"
        else:
            print("Geçersiz seçim, varsayılan olarak 'both' seçiliyor.")
            mode = "both"
    else:
        mode = args.mode

    print(f"Seçilen mod: {mode}")
    print(f"Playlist'teki videolar {mode} modunda işleniyor...")
    process_playlist(PLAYLIST_URL, OUTPUT_DIR, TRANSCRIPTIONS_DIR, mode, audio_format="mp3")
    print("Tüm işlemler tamamlandı!")

if __name__ == "__main__":
    main()
    
    