import os
import zipfile
import shutil
from datetime import datetime
from fastapi import HTTPException
from backend.db import add_notification

def get_backups_dir():
    storage_path = os.environ.get("STORAGE_PATH", "/app/storage")
    backups_dir = os.path.join(storage_path, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    return backups_dir

def create_system_backup():
    storage_path = os.environ.get("STORAGE_PATH", "/app/storage")
    backups_dir = get_backups_dir()
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"sachdeploy_backup_{timestamp}.zip"
    backup_path = os.path.join(backups_dir, backup_filename)
    
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add SQLite DB
            db_file = os.path.join(storage_path, "db.sqlite")
            if os.path.exists(db_file):
                zf.write(db_file, arcname="db.sqlite")
                
            # Add Projects directory
            projects_dir = os.path.join(storage_path, "projects")
            if os.path.exists(projects_dir):
                for root, dirs, files in os.walk(projects_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, storage_path)
                        zf.write(file_path, arcname=arcname)
                        
        size_mb = round(os.path.getsize(backup_path) / (1024 * 1024), 2)
        add_notification("backup", f"System backup created: {backup_filename} ({size_mb} MB)")
        return {
            "status": "success",
            "filename": backup_filename,
            "path": backup_path,
            "size_mb": size_mb,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        if os.path.exists(backup_path):
            try: os.remove(backup_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"Backup creation failed: {e}")

def list_system_backups():
    backups_dir = get_backups_dir()
    results = []
    if not os.path.exists(backups_dir):
        return results
        
    for file in os.listdir(backups_dir):
        if file.endswith(".zip") and file.startswith("sachdeploy_backup_"):
            path = os.path.join(backups_dir, file)
            stat = os.stat(path)
            results.append({
                "filename": file,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results

def restore_system_backup(filename: str):
    storage_path = os.environ.get("STORAGE_PATH", "/app/storage")
    backups_dir = get_backups_dir()
    backup_path = os.path.join(backups_dir, os.path.basename(filename))
    
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Backup file not found")
        
    try:
        with zipfile.ZipFile(backup_path, 'r') as zf:
            zf.extractall(storage_path)
        add_notification("restore", f"System successfully restored from backup: {filename}")
        return {"status": "success", "message": f"Restored from {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")

def delete_system_backup(filename: str):
    backups_dir = get_backups_dir()
    backup_path = os.path.join(backups_dir, os.path.basename(filename))
    if os.path.exists(backup_path):
        os.remove(backup_path)
    return {"status": "success"}
