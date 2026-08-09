import os
import time
import threading
import requests
from fastapi import FastAPI
from database import init_db, is_video_processed, mark_video_processed

# Configurações
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCiRQPr07mu_mS-4SP6HMqvQ")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

app = FastAPI(title="BlackHouse Esports AutoPost")

def download_video_cobalt(video_id: str) -> str:
    """Baixa o vídeo usando a API pública do Cobalt, evitando bloqueios de bot do YouTube"""
    output_filename = f"short_{video_id}.mp4"
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    payload = {
        "url": url,
        "vCodec": "h264" # Garante o formato mp4 padrão aceito pelo TikTok
    }
    
    print(f"[-] Solicitando download via Cobalt para: {video_id}", flush=True)
    res = requests.post(api_url, json=payload, headers=headers)
    
    if res.status_code != 200:
        raise Exception(f"Erro na API do Cobalt (Status {res.status_code}): {res.text}")
        
    data = res.json()
    
    # O Cobalt retorna o link direto de download no campo "url"
    download_url = data.get("url")
    if not download_url:
        raise Exception(f"Falha ao obter link de download no Cobalt: {data}")
    
    print(f"[-] Baixando arquivo mp4...", flush=True)
    video_res = requests.get(download_url, stream=True)
    
    with open(output_filename, "wb") as f:
        for chunk in video_res.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                
    return output_filename

def check_new_shorts():
    uploads_playlist_id = "UU" + YOUTUBE_CHANNEL_ID[2:]
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=5&key={YOUTUBE_API_KEY}"
    
    try:
        items = requests.get(url).json().get("items", [])
    except Exception as e: 
        print(f"[!] Erro ao buscar vídeos na API: {e}", flush=True)
        return
    
    for item in items:
        video_id = item["snippet"]["resourceId"]["videoId"]
        if is_video_processed(video_id): 
            continue
        
        print(f"[-] Analisando: {video_id}", flush=True)
        try:
            mp4_file = download_video_cobalt(video_id)
            print(f"[✓] Vídeo baixado! (Pronto para upload TikTok)", flush=True)
            
            # ---------------------------------------------------------
            # SEU CÓDIGO DE UPLOAD PARA O TIKTOK VAI AQUI
            # ---------------------------------------------------------
            
            # Limpeza do arquivo após upload
            if os.path.exists(mp4_file):
                os.remove(mp4_file)
                
            mark_video_processed(video_id, "Download Sucesso", "OK")
            
        except Exception as e:
            print(f"[!] Erro ao baixar o vídeo {video_id}: {e}", flush=True)
            mark_video_processed(video_id, "Erro download", "ERRO")

def poll_loop():
    while True:
        try: check_new_shorts()
        except: pass
        time.sleep(300)

@app.on_event("startup")
def startup_event():
    init_db()
    threading.Thread(target=poll_loop, daemon=True).start()
