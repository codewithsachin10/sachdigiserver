import os
import sqlite3
import hashlib
import secrets
from datetime import datetime

def get_db_path():
    storage_path = os.environ.get("STORAGE_PATH", "/app/storage")
    os.makedirs(storage_path, exist_ok=True)
    return os.path.join(storage_path, "db.sqlite")

def get_connection():
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        session_token TEXT
    )
    """)
    
    # Create projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL,
        source TEXT NOT NULL,
        port INTEGER NOT NULL,
        internal_port INTEGER NOT NULL,
        container_id TEXT,
        image_name TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Initialize default admin user if not present
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "sachdeploy")
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (admin_user,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                       (admin_user, hash_password(admin_pass)))
        print(f"[SachDeploy DB] Created default user: {admin_user}")
        
    conn.commit()
    conn.close()

# User helpers
def verify_user(username: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, hash_password(password)))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def set_session_token(username: str) -> str:
    token = secrets.token_hex(32)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET session_token = ? WHERE username = ?", (token, username))
    conn.commit()
    conn.close()
    return token

def get_user_by_token(token: str):
    if not token:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE session_token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# Project helpers
def get_all_projects():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_project(project_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_project_by_name(name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_project_db(project_data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
    INSERT INTO projects (
        id, name, type, source, port, internal_port,
        container_id, image_name, status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_data["id"],
        project_data["name"],
        project_data["type"],
        project_data["source"],
        project_data["port"],
        project_data["internal_port"],
        project_data.get("container_id", ""),
        project_data["image_name"],
        project_data.get("status", "building"),
        now
    ))
    conn.commit()
    conn.close()
    return get_project(project_data["id"])

def update_project_status(project_id: str, status: str, container_id: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    if container_id is not None:
        cursor.execute("UPDATE projects SET status = ?, container_id = ? WHERE id = ?", (status, container_id, project_id))
    else:
        cursor.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project_id))
    conn.commit()
    conn.close()

def delete_project_db(project_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
