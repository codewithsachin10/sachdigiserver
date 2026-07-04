import os
import shutil
import subprocess

def clone_repo(repo_url: str, branch: str, target_dir: str):
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    
    cmd = ["git", "clone", "--depth", "1", "--branch", branch or "main", repo_url, target_dir]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        cmd_fallback = ["git", "clone", "--depth", "1", repo_url, target_dir]
        subprocess.run(cmd_fallback, capture_output=True, text=True, check=True)
