import asyncio
import psutil
import time
from backend.database import get_all_projects, update_project_status
from backend.docker import stop_container, get_docker_client

class SystemGuard:
    def __init__(self, ws_manager=None):
        self.ws_manager = ws_manager
        self.running = False

    async def start(self):
        self.running = True
        print("[System Guard] 🛡️ Service started. Monitoring RAM, CPU, and Disk every 5s...")
        while self.running:
            try:
                await self.check_and_protect()
            except Exception as e:
                print(f"[System Guard] Error in loop: {e}")
            await asyncio.sleep(5)

    def stop(self):
        self.running = False

    async def broadcast(self, event: dict):
        if self.ws_manager:
            await self.ws_manager.broadcast(event)

    async def check_and_protect(self):
        mem = psutil.virtual_memory()
        ram_percent = mem.percent
        cpu_percent = psutil.cpu_percent(interval=None)
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent

        # Broadcast live system telemetry
        await self.broadcast({
            "type": "metrics",
            "cpu": round(cpu_percent, 1),
            "ram": round(ram_percent, 1),
            "disk": round(disk_percent, 1),
            "ram_used_mb": round(mem.used / (1024 * 1024)),
            "ram_total_mb": round(mem.total / (1024 * 1024))
        })

        # 1. RAM Guard (> 85%) -> Stop lowest priority/newest container to prevent OS OOM crash
        if ram_percent > 85.0:
            print(f"[System Guard] 🚨 ALERT: High RAM Usage ({ram_percent}%)! Activating emergency container stop...")
            projects = get_all_projects()
            running = [p for p in projects if p.get("status") == "running"]
            if running:
                # Stop the newest launched project to preserve system stability
                target = running[0]
                try:
                    stop_container(target.get("container_id") or f"app-{target['name']}")
                    update_project_status(target["id"], "stopped (guard)")
                    msg = f"🚨 RAM Spike Alert ({ram_percent}%)! System Guard emergency stopped app '{target['name']}' to prevent server crash."
                    print(f"[System Guard] {msg}")
                    await self.broadcast({"type": "guard_warning", "message": msg})
                    await self.broadcast({"type": "status_update"})
                except Exception as e:
                    print(f"[System Guard] Failed to emergency stop container: {e}")

        # 2. CPU Guard (> 90%) -> Warn or throttle
        if cpu_percent > 90.0:
            msg = f"⚠️ High CPU Load ({cpu_percent}%) detected on server host!"
            await self.broadcast({"type": "guard_warning", "message": msg})

        # 3. Disk Guard (> 90%) -> Automatically clean Docker build caches & dangling images
        if disk_percent > 90.0:
            print(f"[System Guard] 🧹 High Disk Usage ({disk_percent}%)! Running automated Docker cleanup...")
            try:
                client = get_docker_client()
                client.images.prune(filters={"dangling": True})
                client.containers.prune()
                msg = f"🧹 Disk usage exceeded {disk_percent}%. System Guard pruned dangling Docker images and stopped containers."
                await self.broadcast({"type": "guard_warning", "message": msg})
            except Exception as e:
                print(f"[System Guard] Disk cleanup error: {e}")
