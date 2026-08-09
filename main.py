import os
import time
import threading
import requests
import isodate
import yt_dlp
from fastapi import FastAPI
from database import init_db, is_video_processed, mark_video_processed

# Configurações com suas credenciais
YOUTUBE_API_KEY = "AIzaSyDteDUQSM0KSnQG_4JYFgYVEOHdi75P5Pg"
YOUTUBE_CHANNEL_ID = "UCiRQPr07mu_mS-4SP6HMqvQ"

TIKTOK_CLIENT_KEY = "awqz2c2pjmuwwnzf"
TIKTOK_CLIENT_SECRET = "LAsYwINgPl7tohKq8HDR3A1KgruSFi3y"
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

app = FastAPI(title="BlackHouse Esports AutoPost")

def is_youtube_short(video_id: str) -> tuple[bool, str]:
    url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails,snippet&id={video_id}&key={YOUTUBE_API_KEY}"
    res = requests.get(url).json()
    
    if not res.get("items"):
        return False, ""
    
    item = res["items"][0]
    title = item["snippet"]["title"]
    duration_iso = item["contentDetails"]["duration"]
    duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
    
    if duration_seconds > 180:
        return False, title

    shorts_url = f"https://www.youtube.com/shorts/{video_id}"
    response = requests.head(shorts_url, allow_redirects=False)
    is_short = response.status_code in [200, 302]
    
    return is_short, title

def download_short_mp4(video_id: str) -> str:
    output_filename = f"short_{video_id}.mp4"
    url = f"https://www.youtube.com/shorts/{video_id}"
    
    # Se a variável de cookies existir na Railway, grava num arquivo temporário
    cookie_path = None
    cookies_content = os.getenv("YOUTUBE_COOKIES", "").strip()
    if cookies_content:
        cookie_path = "cookies.txt"
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(cookies_content)
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True
    }
    
    # Se gerou o arquivo de cookies, passa para o yt-dlp
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    finally:
        # Remove o arquivo temporário de cookies depois do download
        if cookie_path and os.path.exists(cookie_path):
            os.remove(cookie_path)
        
    return output_filename

def upload_to_tiktok(video_path: str, title: str) -> str:
    file_size = os.path.getsize(video_path)
    init_url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
        
    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    payload = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1
        }
    }
    
    init_res = requests.post(init_url, json=payload, headers=headers).json()
    if "data" not in init_res or "upload_url" not in init_res["data"]:
        raise Exception(f"Erro ao inicializar upload no TikTok: {init_res}")
        
    upload_url = init_res["data"]["upload_url"]
    publish_id = init_res["data"]["publish_id"]
    
    with open(video_path, "rb") as f:
        video_bytes = f.read()
        
    put_headers = {
        "Content-Type": "video/mp4",
        "Content-Length": str(file_size),
        "Content-Range": f"bytes 0-{file_size - 1}/{file_size}"
    }
    
    upload_res = requests.put(upload_url, data=video_bytes, headers=put_headers)
    if upload_res.status_code not in [200, 201]:
        raise Exception(f"Erro no upload do vídeo: {upload_res.text}")
        
    return publish_id

def check_new_shorts():
    uploads_playlist_id = "UU" + YOUTUBE_CHANNEL_ID[2:]
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=5&key={YOUTUBE_API_KEY}"
    res = requests.get(url).json()
    
    for item in res.get("items", []):
        video_id = item["snippet"]["resourceId"]["videoId"]
        
        if is_video_processed(video_id):
            continue

        is_short, title = is_youtube_short(video_id)
        if not is_short:
            continue

        print(f"[+] Novo Short encontrado: {title} ({video_id})")
        mp4_file = None
        try:
            mp4_file = download_short_mp4(video_id)
            publish_id = upload_to_tiktok(mp4_file, title)
            mark_video_processed(video_id, title, publish_id)
            print(f"[✓] Vídeo enviado com sucesso para a caixa de entrada do TikTok!")
        except Exception as e:
            print(f"[!] Erro ao processar o vídeo {video_id}: {e}")
        finally:
            if mp4_file and os.path.exists(mp4_file):
                os.remove(mp4_file)

def poll_loop():
    while True:
        try:
            check_new_shorts()
        except Exception as e:
            print(f"[!] Erro na verificação: {e}")
        time.sleep(120)  # Checa a cada 2 minutos

@app.on_event("startup")
def startup_event():
    init_db()
    threading.Thread(target=poll_loop, daemon=True).start()

@app.get("/")
def health_check():
    return {"status": "online", "org": "BlackHouse Esports"}
