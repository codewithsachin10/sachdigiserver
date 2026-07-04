import secrets
from datetime import datetime
from backend.database.connection import get_connection
from backend.database.models import hash_password

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
    cursor.execute("""
    INSERT INTO deployments (project_id, version, commit_hash, commit_msg, author, duration, status, created_at)
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
    cursor.execute("DELETE FROM environment_variables WHERE project_id = ?", (project_id,))
    for k, v in env_dict.items():
        cursor.execute("INSERT INTO project_env (project_id, key, value) VALUES (?, ?, ?)", (project_id, k, str(v)))
        cursor.execute("INSERT INTO environment_variables (project_id, key, value) VALUES (?, ?, ?)", (project_id, k, str(v)))
    conn.commit()
    conn.close()

def get_active_apps_count() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM projects WHERE status = 'running'")
    row = cursor.fetchone()
    conn.close()
    return int(row["cnt"]) if row and "cnt" in row.keys() else (int(row[0]) if row else 0)
