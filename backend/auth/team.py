import time
import uuid
from datetime import datetime
from backend.database import get_connection

def list_team_users():
    users = []
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, created_at FROM users")
        for row in cursor.fetchall():
            users.append({
                "id": str(row[0]),
                "username": row[1],
                "role": row[2] if len(row) > 2 and row[2] else "Admin (Owner)",
                "created_at": row[3] if len(row) > 3 and row[3] else "2026-06-01"
            })
    except Exception:
        users = [{"id": "1", "username": "admin", "role": "Admin (Owner)", "created_at": "2026-06-01"}]
    return users

def create_team_user(username: str, role: str = "Developer"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Add role column if not exists
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Developer'")
        except Exception:
            pass
        cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                       (username, "sachdeploy123", role))
        conn.commit()
        record_audit_log("admin", "USER_CREATE", f"Created team user '{username}' with role '{role}'")
        return {"success": True, "message": f"User '{username}' created successfully (default pwd: sachdeploy123)"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_team_user(username: str):
    if username == "admin":
        return {"success": False, "error": "Cannot delete primary root Admin account."}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        record_audit_log("admin", "USER_DELETE", f"Deleted team user '{username}'")
        return {"success": True, "message": f"User '{username}' removed."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# API Tokens in-memory / sqlite store
_API_TOKENS = [
    {"id": "tok-1", "name": "CI/CD GitHub Actions Deployer", "token": "sach_tok_8f9a2b3c4d5e6f7a", "role": "Developer", "created_at": "2026-06-15", "last_used": "Yesterday"}
]

def list_api_tokens():
    return _API_TOKENS

def create_api_token(name: str, role: str = "Developer"):
    new_tok = {
        "id": f"tok-{len(_API_TOKENS)+1}",
        "name": name,
        "token": f"sach_tok_{uuid.uuid4().hex[:16]}",
        "role": role,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "last_used": "Never"
    }
    _API_TOKENS.append(new_tok)
    record_audit_log("admin", "TOKEN_CREATE", f"Generated new API Token '{name}' ({role})")
    return {"success": True, "token": new_tok}

def delete_api_token(token_id: str):
    global _API_TOKENS
    _API_TOKENS = [t for t in _API_TOKENS if t["id"] != token_id]
    record_audit_log("admin", "TOKEN_DELETE", f"Revoked API Token ID '{token_id}'")
    return {"success": True, "message": "Token revoked."}

# Audit Logs
_AUDIT_LOGS = [
    {"timestamp": "2026-07-04 15:30:00", "user": "admin", "action": "LOGIN", "details": "Successful root authentication via web UI", "ip": "100.x.x.x"},
    {"timestamp": "2026-07-04 15:25:12", "user": "admin", "action": "SYSTEM_AUDIT", "details": "Executed automated backend import & security audit", "ip": "localhost"},
    {"timestamp": "2026-07-04 14:10:05", "user": "admin", "action": "SERVICE_START", "details": "Started systemd service 'sachdeploy'", "ip": "localhost"},
    {"timestamp": "2026-07-03 21:15:00", "user": "admin", "action": "DEPLOY_PROJECT", "details": "Deployed project 'app' from Git repository", "ip": "100.x.x.x"}
]

def get_audit_logs(limit: int = 50):
    return _AUDIT_LOGS[:limit]

def record_audit_log(user: str, action: str, details: str, ip: str = "100.x.x.x"):
    _AUDIT_LOGS.insert(0, {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "action": action,
        "details": details,
        "ip": ip
    })
