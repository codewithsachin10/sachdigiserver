import subprocess
import platform
import os
import threading

def get_system_updates():
    apt_count = 0
    apt_list = []
    try:
        if platform.system() == "Linux" and os.path.exists("/usr/bin/apt-get"):
            res = subprocess.run(["apt-get", "-s", "upgrade"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            if res.returncode == 0:
                for line in res.stdout.split("\n"):
                    if "Inst " in line:
                        pkg = line.split()[1]
                        apt_list.append(pkg)
                apt_count = len(apt_list)
    except Exception:
        pass

    # Check Git version / self update
    git_branch = "main"
    git_commit = "Unknown"
    git_behind = 0
    try:
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdout=subprocess.PIPE, text=True, timeout=1)
        if res.returncode == 0:
            git_branch = res.stdout.strip()
        res_hash = subprocess.run(["git", "rev-parse", "--short", "HEAD"], stdout=subprocess.PIPE, text=True, timeout=1)
        if res_hash.returncode == 0:
            git_commit = res_hash.stdout.strip()
            
        res_behind = subprocess.run(["git", "status", "-sb"], stdout=subprocess.PIPE, text=True, timeout=1)
        if res_behind.returncode == 0 and "[behind" in res_behind.stdout:
            parts = res_behind.stdout.split("[behind")[1].split("]")[0]
            git_behind = int(parts.strip())
    except Exception:
        pass

    return {
        "ubuntu_updates": {
            "count": apt_count,
            "packages": apt_list[:20],
            "status": f"{apt_count} updates available" if apt_count > 0 else "System OS is up to date"
        },
        "docker_updates": {
            "status": "Up to date (Managed via apt / repo)",
            "can_update": apt_count > 0 and any("docker" in p.lower() for p in apt_list)
        },
        "sachdeploy_updates": {
            "branch": git_branch,
            "commit": git_commit,
            "behind_commits": git_behind,
            "status": f"Behind by {git_behind} commit(s)" if git_behind > 0 else "Up to date with origin/main"
        }
    }

def trigger_system_update(target: str):
    valid_targets = ["ubuntu", "docker", "sachdeploy", "all"]
    if target not in valid_targets:
        return {"success": False, "error": f"Invalid update target: {target}"}
        
    def _run_bg():
        try:
            if target in ["ubuntu", "all"]:
                subprocess.run(["sudo", "apt-get", "update", "-y"], timeout=60)
                subprocess.run(["sudo", "apt-get", "upgrade", "-y"], timeout=300)
            if target in ["sachdeploy", "all"]:
                subprocess.run(["git", "pull", "origin", "main"], timeout=30)
        except Exception as e:
            print(f"[SystemUpdate] Error during update execution: {e}")
            
    threading.Thread(target=_run_bg, daemon=True).start()
    return {"success": True, "message": f"Background upgrade triggered for target '{target}'"}
