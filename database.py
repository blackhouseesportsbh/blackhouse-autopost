import sqlite3

DB_NAME = "processed_shorts.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            tiktok_publish_id TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_video_processed(video_id: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_videos WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def mark_video_processed(video_id: str, title: str, tiktok_publish_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO processed_videos (video_id, title, tiktok_publish_id) VALUES (?, ?, ?)",
        (video_id, title, tiktok_publish_id)
    )
    conn.commit()
    conn.close()