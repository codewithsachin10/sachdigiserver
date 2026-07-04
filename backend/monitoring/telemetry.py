import os
import time
import socket
import platform
import subprocess
import psutil
from datetime import datetime
from backend.database import get_all_projects, get_deploy_history
from backend.docker import get_docker_client

_LAST_IO_STATS = {
    "time": 0,
    "disk_read": 0,
    "disk_write": 0,
    "net_sent": 0,
    "net_recv": 0
}

def get_os_info():
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=")[1].strip().strip('"')
    except Exception:
        pass
    return f"{platform.system()} {platform.release()}"

def get_tailscale_ip():
    try:
        res = subprocess.run(["tailscale", "ip", "-4"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return "N/A"

def get_tailscale_status():
    try:
        res = subprocess.run(["tailscale", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        return "connected" if res.returncode == 0 else "disconnected"
    except Exception:
        return "not running"

def get_internet_status():
    try:
        with socket.create_connection(("8.8.8.8", 53), timeout=1.5):
            return "online"
    except Exception:
        return "offline"

def get_cpu_temp():
    try:
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                temp = float(f.read().strip())
                return round(temp / 1000.0, 1) if temp > 100 else round(temp, 1)
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current and entry.current > 0:
                        return round(entry.current, 1)
    except Exception:
        pass
    return None # Return None instead of mock data if thermal sensor inaccessible

def get_system_telemetry():
    global _LAST_IO_STATS
    now = time.time()
    
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage('/')
    cpu_load = psutil.cpu_percent(interval=None)
    
    # CPU frequency & load averages
    freq_current = 0.0
    try:
        freq = psutil.cpu_freq()
        if freq:
            freq_current = round(freq.current, 1)
    except Exception:
        pass
        
    load_avg = [0.0, 0.0, 0.0]
    try:
        if hasattr(os, "getloadavg"):
            load_avg = [round(x, 2) for x in os.getloadavg()]
    except Exception:
        pass
        
    # IO Speed calculation
    disk_read_speed = 0.0
    disk_write_speed = 0.0
    net_up_speed = 0.0
    net_down_speed = 0.0
    
    try:
        dio = psutil.disk_io_counters()
        nio = psutil.net_io_counters()
        
        if _LAST_IO_STATS["time"] > 0:
            dt = max(now - _LAST_IO_STATS["time"], 0.1)
            disk_read_speed = round((dio.read_bytes - _LAST_IO_STATS["disk_read"]) / dt / 1024, 1) # KB/s
            disk_write_speed = round((dio.write_bytes - _LAST_IO_STATS["disk_write"]) / dt / 1024, 1) # KB/s
            net_up_speed = round((nio.bytes_sent - _LAST_IO_STATS["net_sent"]) / dt / 1024, 1) # KB/s
            net_down_speed = round((nio.bytes_recv - _LAST_IO_STATS["net_recv"]) / dt / 1024, 1) # KB/s
            
            # Clamp negative values if counters wrapped
            disk_read_speed = max(0.0, disk_read_speed)
            disk_write_speed = max(0.0, disk_write_speed)
            net_up_speed = max(0.0, net_up_speed)
            net_down_speed = max(0.0, net_down_speed)
            
        if dio:
            _LAST_IO_STATS["disk_read"] = dio.read_bytes
            _LAST_IO_STATS["disk_write"] = dio.write_bytes
        if nio:
            _LAST_IO_STATS["net_sent"] = nio.bytes_sent
            _LAST_IO_STATS["net_recv"] = nio.bytes_recv
        _LAST_IO_STATS["time"] = now
    except Exception as e:
        pass

    docker_version = "Unknown"
    docker_status = "offline"
    running_containers = 0
    stopped_containers = 0
    images_count = 0
    volumes_count = 0
    networks_count = 0
    
    try:
        client = get_docker_client()
        ver = client.version()
        docker_version = ver.get("Version", "Unknown")
        docker_status = "online"
        
        containers = client.containers.list(all=True)
        for c in containers:
            if c.status == "running":
                running_containers += 1
            else:
                stopped_containers += 1
                
        images_count = len(client.images.list())
        volumes_count = len(client.volumes.list())
        networks_count = len(client.networks.list())
    except Exception as e:
        pass
        
    # Versions of tooling
    python_version = platform.python_version()
    git_version = "Unknown"
    try:
        res = subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1)
        if res.returncode == 0:
            git_version = res.stdout.strip().replace("git version ", "")
    except Exception:
        pass

    compose_version = "Unknown"
    try:
        res = subprocess.run(["docker", "compose", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1)
        if res.returncode == 0:
            compose_version = res.stdout.strip().replace("Docker Compose version ", "")
    except Exception:
        pass

    projects = get_all_projects()
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    history = get_deploy_history()
    deployments_today = len([h for h in history if h.get("created_at", "").startswith(today_str)])
    last_deploy = history[0]["created_at"] if history else "Never"
    
    boot_time_sec = int(psutil.boot_time())
    uptime_sec = int(time.time() - boot_time_sec)
    running_procs = len(psutil.pids())
    
    return {
        "hostname": socket.gethostname(),
        "os": get_os_info(),
        "kernel": platform.release(),
        "docker_version": docker_version,
        "compose_version": compose_version,
        "python_version": python_version,
        "git_version": git_version,
        "docker_status": docker_status,
        "tailscale_ip": get_tailscale_ip(),
        "tailscale_status": get_tailscale_status(),
        "internet_status": get_internet_status(),
        "boot_time": datetime.fromtimestamp(boot_time_sec).strftime("%Y-%m-%d %H:%M:%S"),
        "uptime_seconds": uptime_sec,
        "running_processes": running_procs,
        "cpu_percent": round(cpu_load, 1),
        "cpu_freq_mhz": freq_current,
        "load_averages": load_avg,
        "ram_percent": round(mem.percent, 1),
        "ram_used_mb": round(mem.used / (1024 * 1024)),
        "ram_total_mb": round(mem.total / (1024 * 1024)),
        "swap_percent": round(swap.percent, 1),
        "swap_used_mb": round(swap.used / (1024 * 1024)),
        "swap_total_mb": round(swap.total / (1024 * 1024)),
        "disk_percent": round(disk.percent, 1),
        "disk_used_gb": round(disk.used / (1024**3), 1),
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "disk_read_kb_s": disk_read_speed,
        "disk_write_kb_s": disk_write_speed,
        "net_up_kb_s": net_up_speed,
        "net_down_kb_s": net_down_speed,
        "temperature": get_cpu_temp(),
        "docker_stats": {
            "running_containers": running_containers,
            "stopped_containers": stopped_containers,
            "images": images_count,
            "volumes": volumes_count,
            "networks": networks_count
        },
        "projects_count": len(projects),
        "deployments_today": deployments_today,
        "last_deployment": last_deploy,
        "avg_ram_mb": round((mem.used / (1024 * 1024)) / max(running_containers, 1), 1) if running_containers > 0 else 0,
        "avg_cpu_percent": round(cpu_load / max(running_containers, 1), 1) if running_containers > 0 else 0
    }
