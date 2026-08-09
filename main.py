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

def download_video_ytdlp(video_id: str) -> str:
    """Baixa o vídeo usando a biblioteca oficial do yt-dlp com autenticação via cookies"""
    output_filename = f"short_{video_id}.mp4"
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Configurações do yt-dlp para baixar a melhor qualidade em mp4
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_filename,
        'cookiefile': 'cookies.txt',  # O arquivo de cookies deve estar na mesma pasta deste script no Railway
        'quiet': True,
        'no_warnings': True,
    }

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
            # Substituída a função antiga pela nova do yt-dlp
            mp4_file = download_video_ytdlp(video_id)
            print(f"[✓] Vídeo baixado! (Pronto para upload TikTok)", flush=True)
            
            # ---------------------------------------------------------
            # AQUI VOCÊ MANTÉM SEU CÓDIGO DE UPLOAD PARA O TIKTOK
            # ---------------------------------------------------------
            
            # Limpa o arquivo local após o upload para não lotar o servidor
            if os.path.exists(mp4_file):
                os.remove(mp4_file)
                
            mark_video_processed(video_id, "Download Sucesso", "OK")
            
        except Exception as e:
            print(f"[!] Erro crítico ao processar o vídeo {video_id}: {e}", flush=True)
            # Se der erro, marca como erro pra não ficar tentando o dia todo
            mark_video_processed(video_id, "Erro download", "ERRO")

def poll_loop():
    while True:
        try: 
            check_new_shorts()
        except Exception as e: 
            print(f"[!] Erro no loop principal: {e}", flush=True)
        
        # Aguarda 5 minutos antes de checar o canal novamente
        time.sleep(300)

@app.on_event("startup")
def startup_event():
    init_db()
    # Inicia a thread em background para não travar a API do FastAPI
    threading.Thread(target=poll_loop, daemon=True).start()
