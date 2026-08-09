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

def download_video_snapsave(video_id: str) -> str:
    """Baixa o vídeo usando a API pública de download (sem passar pelo youtube-dl)"""
    output_filename = f"short_{video_id}.mp4"
    url = f"https://www.youtube.com/shorts/{video_id}"
    
    # Chama o serviço de download de terceiros
    api_url = "https://snapsave.io/api/ajax/ajaxYoutubeDownload/convert"
    payload = {"vid": video_id, "k": "mp4"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    res = requests.post(api_url, data=payload, headers=headers).json()
    
    if "data" not in res:
        raise Exception(f"Falha na API de download: {res}")
        
    # Pega o link de download direto (o primeiro disponível)
    video_url = res['data']['video'][0]['url']
    
    video_res = requests.get(video_url, stream=True)
    with open(output_filename, "wb") as f:
        for chunk in video_res.iter_content(chunk_size=8192):
            f.write(chunk)
            
    return output_filename

def check_new_shorts():
    uploads_playlist_id = "UU" + YOUTUBE_CHANNEL_ID[2:]
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=5&key={YOUTUBE_API_KEY}"
    
    try:
        items = requests.get(url).json().get("items", [])
    except: return
    
    for item in items:
        video_id = item["snippet"]["resourceId"]["videoId"]
        if is_video_processed(video_id): continue
        
        print(f"[-] Analisando: {video_id}", flush=True)
        try:
            mp4_file = download_video_snapsave(video_id)
            print(f"[✓] Vídeo baixado! (Pronto para upload TikTok)", flush=True)
            # AQUI VOCÊ MANTÉM SEU CÓDIGO DE UPLOAD PARA O TIKTOK
            os.remove(mp4_file)
            mark_video_processed(video_id, "Download Sucesso", "OK")
        except Exception as e:
            print(f"[!] Erro ao baixar via API: {e}", flush=True)
            # Se der erro, marca como erro pra não ficar tentando o dia todo
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
