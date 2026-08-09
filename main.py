import os
import time
import threading
import requests
import isodate
import yt_dlp
from fastapi import FastAPI
from database import init_db, is_video_processed, mark_video_processed

# Configurações
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCiRQPr07mu_mS-4SP6HMqvQ")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

app = FastAPI(title="BlackHouse Esports AutoPost")

def download_short_mp4(video_id: str) -> str:
    output_filename = f"short_{video_id}.mp4"
    url = f"https://www.youtube.com/shorts/{video_id}"
    
    # Tentativa com cookies via variável de ambiente (se existirem)
    cookie_path = None
    if os.getenv("YOUTUBE_COOKIES"):
        cookie_path = "cookies.txt"
        with open(cookie_path, "w") as f: f.write(os.getenv("YOUTUBE_COOKIES"))

    ydl_opts = {
        'format': 'best',
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookie_path if cookie_path else None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    finally:
        if cookie_path and os.path.exists(cookie_path): os.remove(cookie_path)
        
    if not os.path.exists(output_filename):
        raise Exception("Falha crítica no download pelo yt-dlp")
    return output_filename

def check_new_shorts():
    uploads_playlist_id = "UU" + YOUTUBE_CHANNEL_ID[2:]
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=5&key={YOUTUBE_API_KEY}"
    items = requests.get(url).json().get("items", [])
    
    for item in items:
        video_id = item["snippet"]["resourceId"]["videoId"]
        if is_video_processed(video_id): continue
        
        print(f"[-] Tentando baixar: {video_id}", flush=True)
        try:
            mp4_file = download_short_mp4(video_id)
            # Se chegou aqui, baixou. Agora tenta subir.
            # (Aqui entraria sua lógica de upload)
            print(f"[✓] Baixado: {video_id}", flush=True)
            os.remove(mp4_file)
        except Exception as e:
            print(f"[!] Erro no vídeo {video_id}: {e}", flush=True)
            # Se der erro de "bot", marca como processado pra ele não tentar mais
            if "Sign in" in str(e): mark_video_processed(video_id, "ERRO_ROBO", "ERRO")

def poll_loop():
    while True:
        try: check_new_shorts()
        except: pass
        time.sleep(300) # Aumentei pra 5 minutos pra evitar rate limit

@app.on_event("startup")
def startup_event():
    init_db()
    threading.Thread(target=poll_loop, daemon=True).start()
