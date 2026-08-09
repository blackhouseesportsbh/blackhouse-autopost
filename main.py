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

app = FastAPI(title="BlackHouse Esports AutoPost")

def setup_cookies():
    """Gera o arquivo cookies.txt a partir da variável de ambiente do Railway"""
    cookies_content = os.getenv("YOUTUBE_COOKIES", "")
    if cookies_content:
        with open("cookies.txt", "w") as f:
            f.write(cookies_content)
        return "cookies.txt"
    return None

def download_video_ytdlp(video_id: str) -> str:
    """Baixa o vídeo usando yt-dlp com autenticação via cookies"""
    output_filename = f"short_{video_id}.mp4"
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Prepara os cookies
    cookie_path = setup_cookies()

    # CORREÇÃO APLICADA AQUI: Formato simplificado para evitar erro de indisponibilidade
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
    }

    # Se a variável de cookies existir, injeta no yt-dlp
    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path
    else:
        print("[!] AVISO: Variável YOUTUBE_COOKIES não encontrada no Railway. O download pode falhar.", flush=True)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_filename
    except Exception as e:
        raise Exception(f"Erro no yt-dlp: {e}")

def check_new_shorts():
    uploads_playlist_id = "UU" + YOUTUBE_CHANNEL_ID[2:]
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=5&key={YOUTUBE_API_KEY}"
    
    try:
        items = requests.get(url).json().get("items", [])
    except Exception as e: 
        print(f"[!] Erro ao buscar vídeos na API do YouTube: {e}", flush=True)
        return
    
    for item in items:
        video_id = item["snippet"]["resourceId"]["videoId"]
        if is_video_processed(video_id): 
            continue
        
        print(f"[-] Analisando: {video_id}", flush=True)
        try:
            mp4_file = download_video_ytdlp(video_id)
            print(f"[✓] Vídeo baixado! (Pronto para upload TikTok)", flush=True)
            
            # ---------------------------------------------------------
            # SEU CÓDIGO DE UPLOAD PARA O TIKTOK VAI AQUI
            # ---------------------------------------------------------
            
            # Limpa o arquivo local para não lotar o disco do Railway
            if os.path.exists(mp4_file):
                os.remove(mp4_file)
                
            mark_video_processed(video_id, "Download Sucesso", "OK")
            
        except Exception as e:
            print(f"[!] Erro crítico ao processar o vídeo {video_id}: {e}", flush=True)
            mark_video_processed(video_id, "Erro download", "ERRO")

def poll_loop():
    while True:
        try: 
            check_new_shorts()
        except Exception as e: 
            print(f"[!] Erro no loop principal: {e}", flush=True)
        
        time.sleep(300)

@app.on_event("startup")
def startup_event():
    init_db()
    threading.Thread(target=poll_loop, daemon=True).start()
