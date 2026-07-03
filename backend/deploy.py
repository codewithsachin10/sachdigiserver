import os
import shutil
import zipfile
import subprocess
from backend.db import update_project_status
from backend.docker_manager import build_image, run_container

def get_storage_dirs():
    storage_path = os.environ.get("STORAGE_PATH", "/app/storage")
    uploads_dir = os.path.join(storage_path, "uploads")
    projects_dir = os.path.join(storage_path, "projects")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(projects_dir, exist_ok=True)
    return uploads_dir, projects_dir

def extract_zip(zip_path: str, target_dir: str):
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
    
    # Flatten single subdirectory if present
    entries = os.listdir(target_dir)
    if len(entries) == 1 and os.path.isdir(os.path.join(target_dir, entries[0])):
        sub_dir = os.path.join(target_dir, entries[0])
        for item in os.listdir(sub_dir):
            os.rename(os.path.join(sub_dir, item), os.path.join(target_dir, item))
        try:
            os.rmdir(sub_dir)
        except:
            pass

def clone_repo(repo_url: str, branch: str, target_dir: str):
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    
    cmd = ["git", "clone", "--depth", "1", "--branch", branch or "main", repo_url, target_dir]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        # Fallback to default branch if branch not specified or different
        cmd_fallback = ["git", "clone", "--depth", "1", repo_url, target_dir]
        subprocess.run(cmd_fallback, capture_output=True, text=True, check=True)

def detect_project_type_and_template(project_dir: str):
    req_path = os.path.join(project_dir, "requirements.txt")
    pkg_path = os.path.join(project_dir, "package.json")
    html_path = os.path.join(project_dir, "index.html")

    docker_dir = "/app/docker" if os.path.exists("/app/docker") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docker")

    if os.path.exists(req_path):
        template_path = os.path.join(docker_dir, "python.Dockerfile")
        return "python", 8000, template_path
    elif os.path.exists(pkg_path):
        template_path = os.path.join(docker_dir, "node.Dockerfile")
        return "node", 3000, template_path
    elif os.path.exists(html_path):
        template_path = os.path.join(docker_dir, "static.Dockerfile")
        return "static", 80, template_path
    else:
        raise ValueError("Cannot detect project type. Root directory must contain requirements.txt (Python), package.json (Node.js), or index.html (Static Site).")

def deploy_project_background(project_id: str, name: str, project_dir: str, image_name: str, host_port: int):
    try:
        update_project_status(project_id, "building")
        
        # 1. Detect project type
        proj_type, internal_port, template_path = detect_project_type_and_template(project_dir)
        
        # 2. Copy predefined Dockerfile template to project directory
        target_dockerfile = os.path.join(project_dir, "Dockerfile")
        shutil.copyfile(template_path, target_dockerfile)
        
        # 3. Build Docker container using template
        build_image(project_dir, image_name)
        
        # 4. Run container
        container_name = f"app-{name}"
        container_id = run_container(image_name, container_name, host_port, internal_port)
        
        # 5. Update SQLite status
        update_project_status(project_id, "running", container_id)
        print(f"[SachDeploy] Successfully deployed {name} on port {host_port}")
    except Exception as e:
        print(f"[SachDeploy] Deployment failed for {name}: {e}")
        update_project_status(project_id, f"error: {str(e)[:40]}")
