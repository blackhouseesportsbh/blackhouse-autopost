import os
import time
import threading
import requests
import isodate
import yt_dlp
from fastapi import FastAPI
from database import init_db, is_video_processed, mark_video_processed

# Configurações com suas credenciais
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCiRQPr07mu_mS-4SP6HMqvQ")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

app = FastAPI(title="BlackHouse Esports AutoPost")

def is_youtube_short(video_id: str) -> tuple[bool, str]:
    url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails,snippet&id={video_id}&key={YOUTUBE_API_KEY}"
    res = requests.get(url).json()
    if not res.get("items"): return False, ""
    item = res["items"][0]
    title = item["snippet"]["title"]
    duration_iso = item["contentDetails"]["duration"]
    duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
    if duration_seconds > 180: return False, title
    shorts_url = f"https://www.youtube.com/shorts/{video_id}"
    response = requests.head(shorts_url, allow_redirects=False)
    return response.status_code in [200, 302], title

def download_short_mp4(video_id: str) -> str:
    output_filename = f"short_{video_id}.mp4"
    url = f"https://www.youtube.com/shorts/{video_id}"
    
    # Configuração 'mobile' para enganar o YouTube e baixar sem precisar de cookies
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_filename

def upload_to_tiktok(video_path: str, title: str) -> str:
    file_size = os.path.getsize(video_path)
    init_url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
    headers = {"Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}", "Content-Type": "application/json; charset=UTF-8"}
    payload = {"source_info": {"source": "FILE_UPLOAD", "video_size": file_size, "chunk_size": file_size, "total_chunk_count": 1}}
    
    init_res = requests.post(init_url, json=payload, headers=headers).json()
    upload_url = init_res["data"]["upload_url"]
    publish_id = init_res["data"]["publish_id"]
    
    with open(video_path, "rb") as f:
        video_bytes = f.read()
    
    put_headers = {"Content-Type": "video/mp4", "Content-Length": str(file_size), "Content-Range": f"bytes 0-{file_size - 1}/{file_size}"}
    requests.put(upload_url, data=video_bytes, headers=put_headers)
    return publish_id

def check_new_shorts():
    uploads_playlist_id = "UU" + YOUTUBE_CHANNEL_ID[2:]
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=5&key={YOUTUBE_API_KEY}"
    items = requests.get(url).json().get("items", [])
    
    for item in items:
        video_id = item["snippet"]["resourceId"]["videoId"]
        title = item["snippet"].get("title", "Sem título")
        if video_id in ["RZORo8iV9UI", "5KUSGlieyj4", "IKfixyS_Ofo"]: continue
        if is_video_processed(video_id): continue
        
        is_short, short_title = is_youtube_short(video_id)
        if not is_short: continue

        mp4_file = None
        try:
            mp4_file = download_short_mp4(video_id)
            publish_id = upload_to_tiktok(mp4_file, short_title)
            mark_video_processed(video_id, short_title, publish_id)
            print(f"[✓] SUCESSO: '{short_title}' enviado!", flush=True)
        except Exception as e:
            print(f"[!] Erro no vídeo {video_id}: {e}", flush=True)
        finally:
            if mp4_file and os.path.exists(mp4_file): os.remove(mp4_file)

def poll_loop():
    while True:
        try: check_new_shorts()
        except: pass
        time.sleep(120)

@app.on_event("startup")
def startup_event():
    init_db()
    threading.Thread(target=poll_loop, daemon=True).start()
