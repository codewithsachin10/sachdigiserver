import os
import shutil
from datetime import datetime
from fastapi import HTTPException

def get_base_dir():
    return os.environ.get("STORAGE_PATH", "/app/storage")

def safe_path(rel_path: str) -> str:
    base = os.path.abspath(get_base_dir())
    clean_rel = rel_path.lstrip("/").replace("..", "")
    full = os.path.abspath(os.path.join(base, clean_rel))
    if not full.startswith(base):
        raise HTTPException(status_code=403, detail="Access denied: Path outside root storage")
    return full

def list_directory(rel_path: str = ""):
    target = safe_path(rel_path)
    if not os.path.exists(target):
        os.makedirs(target, exist_ok=True)
    if not os.path.isdir(target):
        raise HTTPException(status_code=400, detail="Not a directory")
        
    entries = []
    try:
        with os.scandir(target) as it:
            for entry in it:
                stat = entry.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                size = 0 if entry.is_dir() else stat.st_size
                entries.append({
                    "name": entry.name,
                    "path": os.path.join(rel_path, entry.name).lstrip("/"),
                    "is_dir": entry.is_dir(),
                    "size_bytes": size,
                    "mod_time": mod_time
                })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading directory: {e}")
        
    # Sort directories first, then files alphabetically
    entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {"current_path": rel_path, "entries": entries}

def read_file_content(rel_path: str):
    target = safe_path(rel_path)
    if not os.path.exists(target) or os.path.isdir(target):
        raise HTTPException(status_code=404, detail="File not found")
        
    # Limit text read to 500KB for lightweight editor
    if os.path.getsize(target) > 512 * 1024:
        raise HTTPException(status_code=400, detail="File too large for inline editing (> 500KB)")
        
    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"path": rel_path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

def write_file_content(rel_path: str, content: str):
    target = safe_path(rel_path)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "path": rel_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

def create_folder(rel_path: str):
    target = safe_path(rel_path)
    try:
        os.makedirs(target, exist_ok=True)
        return {"status": "success", "path": rel_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating folder: {e}")

def rename_item(old_rel_path: str, new_name: str):
    old_target = safe_path(old_rel_path)
    if not os.path.exists(old_target):
        raise HTTPException(status_code=404, detail="Item not found")
        
    parent_dir = os.path.dirname(old_target)
    clean_new_name = os.path.basename(new_name.replace("..", ""))
    new_target = os.path.join(parent_dir, clean_new_name)
    
    try:
        os.rename(old_target, new_target)
        new_rel = os.path.relpath(new_target, get_base_dir())
        return {"status": "success", "new_path": new_rel}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rename failed: {e}")

def delete_item(rel_path: str):
    target = safe_path(rel_path)
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Item not found")
        
    try:
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
        else:
            os.remove(target)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
