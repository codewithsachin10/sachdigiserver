import os
import subprocess

def get_system_logs(category: str = "all", lines: int = 100):
    lines = min(max(int(lines), 10), 500)
    logs_data = []
    
    if category in ["all", "syslog", "system"]:
        logs_data.extend(_read_log_file("/var/log/syslog", "System Log", lines))
        if not logs_data:
            logs_data.extend(_read_log_file("/var/log/system.log", "System Log (macOS)", lines))
            
    if category in ["all", "kernel", "dmesg"]:
        logs_data.extend(_read_command(["dmesg"], "Kernel / Hardware Buffer (dmesg)", lines))
        
    if category in ["all", "auth", "ssh"]:
        logs_data.extend(_read_log_file("/var/log/auth.log", "SSH & Authentication Log", lines))
        if not logs_data:
            logs_data.extend(_read_log_file("/var/log/secure", "Security & Auth Log", lines))
            
    if category in ["all", "docker"]:
        logs_data.extend(_read_command(["journalctl", "-u", "docker", "-n", str(lines), "--no-pager"], "Docker Daemon Journal", lines))
        
    if not logs_data:
        logs_data.append({
            "timestamp": "Active",
            "source": f"Log Reader ({category})",
            "message": f"No logs available for category '{category}' in restricted environment or host system logs not mounted.",
            "level": "INFO"
        })
        
    return sorted(logs_data, key=lambda x: str(x.get("timestamp", "")), reverse=True)[:lines]

def _read_log_file(path, source, max_lines):
    results = []
    if os.path.exists(path):
        try:
            res = subprocess.run(["tail", "-n", str(max_lines), path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split()
                        ts = " ".join(parts[:3]) if len(parts) > 3 else "Recent"
                        msg = " ".join(parts[3:]) if len(parts) > 3 else line
                        level = "ERROR" if "err" in line.lower() or "fail" in line.lower() else "WARN" if "warn" in line.lower() else "INFO"
                        results.append({
                            "timestamp": ts,
                            "source": source,
                            "message": msg,
                            "level": level
                        })
        except Exception:
            pass
    return results

def _read_command(cmd, source, max_lines):
    results = []
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        if res.returncode == 0 and res.stdout:
            lines = res.stdout.strip().split("\n")[-max_lines:]
            for line in lines:
                if line.strip():
                    level = "ERROR" if "err" in line.lower() or "fail" in line.lower() else "WARN" if "warn" in line.lower() else "INFO"
                    results.append({
                        "timestamp": "Recent",
                        "source": source,
                        "message": line.strip(),
                        "level": level
                    })
    except Exception:
        pass
    return results
