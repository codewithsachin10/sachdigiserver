import os
import sqlite3
import hashlib
import secrets
import json
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
    
    # Create notifications table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        read INTEGER DEFAULT 0
    )
    """)
    
    # Create deploy_history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deploy_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        version TEXT,
        commit_hash TEXT,
        commit_msg TEXT,
        author TEXT,
        duration INTEGER,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # Create project_env table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_env (
        project_id TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY (project_id, key)
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
        
    # Initialize default settings if not present
    defaults = {
        "server_name": "SachDeploy Stable Server",
        "theme": "dark",
        "max_ram_mb": "512",
        "max_cpu_core": "0.5",
        "max_active_apps": "3",
        "port_range_min": "8001",
        "port_range_max": "8100"
    }
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    conn.commit()
    conn.close()

# --- User Helpers ---
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

# --- Project Helpers ---
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
    cursor.execute("DELETE FROM deploy_history WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM project_env WHERE project_id = ?", (project_id,))
    conn.commit()
    conn.close()

# --- Notifications Helpers ---
def add_notification(type_str: str, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO notifications (type, message, timestamp, read) VALUES (?, ?, ?, 0)", (type_str, message, now))
    conn.commit()
    conn.close()

def get_notifications(limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_notifications_read():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET read = 1")
    conn.commit()
    conn.close()

def clear_notifications():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notifications")
    conn.commit()
    conn.close()

# --- Deploy History Helpers ---
def add_deploy_history(project_id: str, version: str, commit_hash: str, commit_msg: str, author: str, duration: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO deploy_history (project_id, version, commit_hash, commit_msg, author, duration, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, version, commit_hash, commit_msg, author, duration, status, now))
    conn.commit()
    conn.close()

def get_deploy_history(project_id: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    if project_id:
        cursor.execute("SELECT * FROM deploy_history WHERE project_id = ? ORDER BY id DESC", (project_id,))
    else:
        cursor.execute("SELECT * FROM deploy_history ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Settings Helpers ---
def get_setting(key: str, default: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

# --- Project Environment Variables Helpers ---
def get_project_env(project_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM project_env WHERE project_id = ?", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

def set_project_env(project_id: str, env_dict: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_env WHERE project_id = ?", (project_id,))
    for k, v in env_dict.items():
        cursor.execute("INSERT INTO project_env (project_id, key, value) VALUES (?, ?, ?)", (project_id, k, str(v)))
    conn.commit()
    conn.close()

def get_active_apps_count() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM projects WHERE status = 'running'")
    row = cursor.fetchone()
    conn.close()
    return int(row["cnt"]) if row and "cnt" in row.keys() else (int(row[0]) if row else 0)

