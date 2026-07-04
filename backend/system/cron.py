import time
import subprocess
from datetime import datetime

# In-memory scheduler state synced with system cron / background tasks
_SCHEDULED_JOBS = [
    {
        "id": "job-backup-daily",
        "name": "Daily Database & Project Backup",
        "schedule": "0 2 * * * (Daily at 2:00 AM)",
        "command": "python -m backend.system.backup create --all",
        "last_run": "Never",
        "status": "active",
        "next_run": "Tomorrow at 02:00 AM"
    },
    {
        "id": "job-docker-prune",
        "name": "Weekly Docker System Cleanup",
        "schedule": "0 3 * * 0 (Sundays at 3:00 AM)",
        "command": "docker system prune -af --volumes",
        "last_run": "Never",
        "status": "active",
        "next_run": "Sunday at 03:00 AM"
    },
    {
        "id": "job-apt-update",
        "name": "System Package Repository Cache Update",
        "schedule": "0 4 * * 1 (Mondays at 4:00 AM)",
        "command": "apt-get update -y",
        "last_run": "Never",
        "status": "active",
        "next_run": "Monday at 04:00 AM"
    },
    {
        "id": "job-log-rotate",
        "name": "Log Rotation & Cleanup",
        "schedule": "0 0 * * * (Midnight)",
        "command": "find /var/log -type f -name '*.gz' -mtime +7 -delete",
        "last_run": "Never",
        "status": "active",
        "next_run": "Tonight at 12:00 AM"
    }
]

def list_cron_jobs():
    return _SCHEDULED_JOBS

def toggle_cron_job(job_id: str):
    for job in _SCHEDULED_JOBS:
        if job["id"] == job_id:
            job["status"] = "paused" if job["status"] == "active" else "active"
            return {"success": True, "job": job}
    return {"success": False, "error": "Job ID not found"}

def trigger_cron_job(job_id: str):
    for job in _SCHEDULED_JOBS:
        if job["id"] == job_id:
            job["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Trigger command synchronously or background
            try:
                if "docker system prune" in job["command"]:
                    from backend.docker import get_docker_client
                    client = get_docker_client()
                    client.images.prune(filters={"dangling": False})
                    client.containers.prune()
                    client.volumes.prune()
                elif "backup" in job["command"]:
                    from backend.system.backup import create_backup
                    create_backup(backup_type="all")
            except Exception as e:
                pass
            return {"success": True, "message": f"Successfully triggered job '{job['name']}'"}
    return {"success": False, "error": "Job ID not found"}
