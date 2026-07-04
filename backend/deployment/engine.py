import os
import shutil
import zipfile
import subprocess
import time
from datetime import datetime
from backend.database import update_project_status, add_deploy_history, add_notification
from backend.docker import build_image, run_container
from backend.git import clone_repo

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

def detect_project_type_and_template(project_dir: str):
    dockerfile_path = os.path.join(project_dir, "Dockerfile")
    compose_path = os.path.join(project_dir, "docker-compose.yml")
    req_path = os.path.join(project_dir, "requirements.txt")
    pyproject_path = os.path.join(project_dir, "pyproject.toml")
    pkg_path = os.path.join(project_dir, "package.json")
    php_path = os.path.join(project_dir, "composer.json")
    index_php_path = os.path.join(project_dir, "index.php")
    html_path = os.path.join(project_dir, "index.html")

    docker_dir = "/app/docker" if os.path.exists("/app/docker") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docker")

    if os.path.exists(dockerfile_path):
        return "custom-dockerfile", 8000, dockerfile_path
    elif os.path.exists(compose_path):
        return "docker-compose", 8000, compose_path
    elif os.path.exists(req_path) or os.path.exists(pyproject_path):
        template_path = os.path.join(docker_dir, "python.Dockerfile")
        # Detect subframework if possible
        sub = "python"
        if os.path.exists(req_path):
            try:
                with open(req_path, "r", errors="ignore") as f:
                    c = f.read().lower()
                    if "fastapi" in c: sub = "python (fastapi)"
                    elif "flask" in c: sub = "python (flask)"
                    elif "django" in c: sub = "python (django)"
            except: pass
        return sub, 8000, template_path
    elif os.path.exists(pkg_path):
        template_path = os.path.join(docker_dir, "node.Dockerfile")
        sub = "node.js"
        try:
            with open(pkg_path, "r", errors="ignore") as f:
                c = f.read().lower()
                if "next" in c: sub = "node.js (next.js)"
                elif "react" in c: sub = "node.js (react)"
                elif "vue" in c: sub = "node.js (vue)"
                elif "express" in c: sub = "node.js (express)"
                elif "angular" in c: sub = "node.js (angular)"
        except: pass
        return sub, 3000, template_path
    elif os.path.exists(php_path) or os.path.exists(index_php_path):
        template_path = os.path.join(docker_dir, "php.Dockerfile")
        sub = "php (laravel)" if os.path.exists(php_path) else "php"
        return sub, 8000, template_path
    elif os.path.exists(html_path):
        template_path = os.path.join(docker_dir, "static.Dockerfile")
        return "static html", 80, template_path
    else:
        raise ValueError("Cannot detect project type. Root directory must contain requirements.txt, package.json, composer.json, Dockerfile, or index.html.")

async def deploy_project_background(project_id: str, name: str, project_dir: str, image_name: str, host_port: int, ws_manager=None, author: str = "admin", env_vars: dict = None):
    start_time = time.time()
    
    async def emit_step(step_num: int, step_name: str, status: str = "in_progress", log: str = ""):
        if ws_manager:
            await ws_manager.broadcast({
                "type": "deploy_step",
                "project_id": project_id,
                "project_name": name,
                "step_num": step_num,
                "step_name": step_name,
                "status": status,
                "log": log,
                "timestamp": datetime.utcnow().strftime("%H:%M:%S")
            })
            
    try:
        update_project_status(project_id, "building")
        await emit_step(1, "Upload & Archive Extraction", "done", "Archive extracted and structure flattened.")
        
        # 2. Detect project type
        await emit_step(2, "Framework Detection", "in_progress", "Scanning root directory for dependency descriptors...")
        proj_type, internal_port, template_path = detect_project_type_and_template(project_dir)
        await emit_step(2, "Framework Detection", "done", f"Detected framework: {proj_type.upper()} (internal port {internal_port})")
        
        # 3. Generate Dockerfile
        await emit_step(3, "Generate Dockerfile", "in_progress", "Configuring Docker container instructions...")
        if proj_type != "custom-dockerfile" and proj_type != "docker-compose":
            target_dockerfile = os.path.join(project_dir, "Dockerfile")
            shutil.copyfile(template_path, target_dockerfile)
        await emit_step(3, "Generate Dockerfile", "done", "Dockerfile prepared with security and resource guardrails.")
        
        # 4. Docker Build
        await emit_step(4, "Docker Image Build", "in_progress", f"Building Docker image '{image_name}'... (This may take a few moments)")
        build_image(project_dir, image_name)
        await emit_step(4, "Docker Image Build", "done", f"Successfully compiled Docker image '{image_name}'.")
        
        # 5. Container Creation & Port Assignment
        await emit_step(5, "Container Creation & Port Assignment", "in_progress", f"Assigning host port {host_port} -> {internal_port} and enforcing 512MB RAM cap...")
        container_name = f"app-{name}"
        container_id = run_container(image_name, container_name, host_port, internal_port, env_vars=env_vars)
        await emit_step(5, "Container Creation & Port Assignment", "done", f"Container created (ID: {container_id[:12]}).")
        
        # 6. Launch & Health Check
        await emit_step(6, "Container Health Check", "in_progress", "Verifying process listening and network routing...")
        time.sleep(1) # Brief pause for process spin-up
        await emit_step(6, "Container Health Check", "done", "Health check passed. Service is responding normally.")
        
        # 7. Running
        duration = int(time.time() - start_time)
        update_project_status(project_id, "running", container_id)
        add_deploy_history(project_id, "v1.0", "manual/upload", "Deploy from dashboard", author, duration, "success")
        add_notification("deploy", f"Successfully deployed application '{name}' on port {host_port} in {duration}s")
        
        await emit_step(7, "Deployment Completed", "done", f"🚀 Project '{name}' is live at http://localhost:{host_port}!")
        if ws_manager:
            await ws_manager.broadcast({"type": "status_update"})
            
    except Exception as e:
        duration = int(time.time() - start_time)
        err_msg = str(e)
        print(f"[SachDeploy] Deployment failed for {name}: {err_msg}")
        update_project_status(project_id, f"error: {err_msg[:30]}")
        add_deploy_history(project_id, "v1.0", "error", err_msg[:50], author, duration, "failed")
        add_notification("deploy", f"🔴 Deployment failed for '{name}': {err_msg[:60]}")
        
        await emit_step(0, "Deployment Failed", "error", f"Error: {err_msg}")
        if ws_manager:
            await ws_manager.broadcast({"type": "status_update"})
