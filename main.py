import os
import time
import threading
import requests
import yt_dlp
from fastapi import FastAPI
from database import init_db, is_video_processed, mark_video_processed

# Configurações
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCiRQPr07mu_mS-4SP6HMqvQ")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

app = FastAPI()

def download_video(video_id: str) -> str:
    output_filename = f"short_{video_id}.mp4"
    url = f"https://www.youtube.com/shorts/{video_id}"
    
    # Configuração de bypass total para evitar bloqueios
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        # Força o uso do identificador de cliente web padrão do Google
        'extractor_args': {'youtube': {'player_client': ['web']}},
        # Adiciona um User-Agent de navegador real
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        
    if not os.path.exists(output_filename):
        raise Exception("Falha ao baixar vídeo após tentativa de bypass.")
    return output_filename

def check_new_shorts():
    uploads_playlist_id = "UU" + YOUTUBE_CHANNEL_ID[2:]
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=3&key={YOUTUBE_API_KEY}"
    items = requests.get(url).json().get("items", [])
    
    for item in items:
        video_id = item["snippet"]["resourceId"]["videoId"]
        if is_video_processed(video_id): continue
        
        print(f"[-] Tentando download: {video_id}", flush=True)
        try:
            path = download_video(video_id)
            print(f"[✓] Sucesso: {path}", flush=True)
            # AQUI VOCÊ MANTÉM SEU CÓDIGO DE UPLOAD DO TIKTOK
            os.remove(path)
            mark_video_processed(video_id, "Sucesso", "OK")
        except Exception as e:
            print(f"[!] Erro crítico: {e}", flush=True)
            # Se der erro, não insiste nesse vídeo por enquanto
            mark_video_processed(video_id, "Erro download", "ERRO")

def poll_loop():
    while True:
        try: check_new_shorts()
        except: pass
        time.sleep(600) # Espera 10 minutos entre checagens para não ser banido pelo YouTube

@app.on_event("startup")
def startup_event():
    init_db()
    threading.Thread(target=poll_loop, daemon=True).start()
