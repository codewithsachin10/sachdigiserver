import os
import sys
import subprocess
import threading
import time
from backend.docker_manager import get_docker_client
from backend.db import add_notification

def restart_sachdeploy_service():
    add_notification("server", "SachDeploy service is restarting...")
    print("[Server Control] Triggering SachDeploy restart in 2 seconds...")
    
    def delayed_exit():
        time.sleep(2)
        os._exit(0) # Docker compose restart policy will bring us right back up!
        
    threading.Thread(target=delayed_exit, daemon=True).start()
    return {"status": "success", "message": "SachDeploy is restarting. Please reconnect in 5 seconds."}

def clear_docker_cache():
    client = get_docker_client()
    try:
        img_res = client.images.prune(filters={"dangling": True})
        cont_res = client.containers.prune()
        vol_res = client.volumes.prune()
        
        reclaimed_mb = round((
            img_res.get("SpaceReclaimed", 0) +
            cont_res.get("SpaceReclaimed", 0) +
            vol_res.get("SpaceReclaimed", 0)
        ) / (1024 * 1024), 2)
        
        msg = f"Cleaned Docker cache. Reclaimed {reclaimed_mb} MB of disk space."
        add_notification("cleanup", msg)
        return {"status": "success", "message": msg, "reclaimed_mb": reclaimed_mb}
    except Exception as e:
        raise RuntimeError(f"Cache cleanup failed: {e}")

def clean_system_logs():
    storage_path = os.environ.get("STORAGE_PATH", "/app/storage")
    logs_dir = os.path.join(storage_path, "logs")
    count = 0
    if os.path.exists(logs_dir):
        for f in os.listdir(logs_dir):
            try:
                os.remove(os.path.join(logs_dir, f))
                count += 1
            except Exception:
                pass
    add_notification("cleanup", f"Cleaned {count} log archives from storage.")
    return {"status": "success", "message": f"Cleaned {count} log archives."}

def reboot_server():
    add_notification("server", "Host OS server reboot initiated by admin.")
    try:
        subprocess.Popen(["sudo", "reboot"])
        return {"status": "success", "message": "Server reboot initiated."}
    except Exception as e:
        return {"status": "warning", "message": f"Could not trigger OS reboot directly ({e}). Please reboot via SSH or Tailscale console."}

def shutdown_server():
    add_notification("server", "Host OS server shutdown initiated by admin.")
    try:
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])
        return {"status": "success", "message": "Server shutdown initiated."}
    except Exception as e:
        return {"status": "warning", "message": f"Could not trigger OS shutdown directly ({e}). Please shutdown via SSH or Tailscale console."}
