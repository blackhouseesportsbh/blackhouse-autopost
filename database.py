import sqlite3
import datetime

# Nome do arquivo do banco de dados que será criado no Railway
DB_NAME = "videos.db"

def get_connection():
    # check_same_thread=False é importante porque usamos uma thread separada para o loop no FastAPI
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    """Inicializa o banco de dados e cria a tabela se ela não existir."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_videos (
            video_id TEXT PRIMARY KEY,
            status TEXT,
            message TEXT,
            processed_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_video_processed(video_id: str) -> bool:
    """Verifica se o vídeo já consta no banco de dados para não baixar de novo."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_videos WHERE video_id = ?", (video_id,))
    result = cursor.fetchone()
    conn.close()
    
    # Retorna True se achou algo, False se não achou
    return result is not None

def mark_video_processed(video_id: str, message: str, status: str):
    """Marca o vídeo como processado (seja com SUCESSO ou ERRO)."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_videos (video_id, status, message, processed_at)
        VALUES (?, ?, ?, ?)
    ''', (video_id, status, message, now))
    
    conn.commit()
    conn.close()
