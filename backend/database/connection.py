import os
import sqlite3

def get_db_path() -> str:
    storage_path = os.environ.get("STORAGE_PATH", "/app/storage")
    os.makedirs(storage_path, exist_ok=True)
    return os.path.join(storage_path, "db.sqlite")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
