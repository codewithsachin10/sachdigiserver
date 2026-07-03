import os
import socket
import docker
from docker.errors import NotFound
from backend.db import get_all_projects

try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"[SachDeploy WARNING] Docker Daemon connection error: {e}")
    docker_client = None

def get_docker_client():
    global docker_client
    if not docker_client:
        try:
            docker_client = docker.from_env()
        except Exception as e:
            raise RuntimeError(f"Cannot connect to Docker Daemon: {e}")
    return docker_client

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_next_free_port() -> int:
    min_port = 8001
    max_port = 8100
    
    projects = get_all_projects()
    assigned_ports = {p["port"] for p in projects if p.get("port")}
    
    for port in range(min_port, max_port + 1):
        if port not in assigned_ports and not is_port_in_use(port):
            return port
    raise RuntimeError("No free ports left in configured range 8001-8100!")

def check_active_apps_limit():
    max_apps = int(os.environ.get("MAX_ACTIVE_APPS", "3"))
    projects = get_all_projects()
    active = len([p for p in projects if p.get("status") == "running"])
    if active >= max_apps:
        raise RuntimeError(f"Maximum active applications limit ({max_apps}) reached on this server!")

def build_image(project_dir: str, image_name: str):
    client = get_docker_client()
    try:
        response = client.api.build(path=project_dir, tag=image_name, rm=True, decode=True)
        for chunk in response:
            if 'error' in chunk:
                raise RuntimeError(f"Docker build failed: {chunk['error'].strip()}")
        return True
    except Exception as e:
        raise RuntimeError(f"Docker image build failed: {str(e)}")

def run_container(image_name: str, container_name: str, host_port: int, internal_port: int) -> str:
    client = get_docker_client()
    
    # Remove old container if present
    try:
        old = client.containers.get(container_name)
        old.stop(timeout=5)
        old.remove()
    except NotFound:
        pass
    except Exception as e:
        print(f"Warning removing old container: {e}")

    # Enforce strict 512MB RAM and 0.5 CPU core limit
    try:
        container = client.containers.run(
            image=image_name,
            name=container_name,
            detach=True,
            restart_policy={"Name": "unless-stopped"},
            ports={f"{internal_port}/tcp": host_port},
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000
        )
        return container.id
    except Exception as e:
        raise RuntimeError(f"Failed to start container: {str(e)}")

def start_container(container_id_or_name: str):
    client = get_docker_client()
    try:
        c = client.containers.get(container_id_or_name)
        c.start()
        return True
    except Exception as e:
        raise RuntimeError(f"Could not start container: {e}")

def stop_container(container_id_or_name: str):
    client = get_docker_client()
    try:
        c = client.containers.get(container_id_or_name)
        c.stop(timeout=5)
        return True
    except Exception as e:
        raise RuntimeError(f"Could not stop container: {e}")

def restart_container(container_id_or_name: str):
    client = get_docker_client()
    try:
        c = client.containers.get(container_id_or_name)
        c.restart(timeout=5)
        return True
    except Exception as e:
        raise RuntimeError(f"Could not restart container: {e}")

def remove_container_and_image(container_id_or_name: str, image_name: str = None):
    client = get_docker_client()
    if container_id_or_name:
        try:
            c = client.containers.get(container_id_or_name)
            c.stop(timeout=3)
            c.remove(force=True)
        except NotFound:
            pass
        except Exception as e:
            print(f"Error removing container: {e}")
            
    if image_name:
        try:
            client.images.remove(image=image_name, force=True)
        except Exception as e:
            print(f"Error removing image: {e}")

def get_container_status(container_id_or_name: str) -> str:
    if not container_id_or_name:
        return "stopped"
    try:
        client = get_docker_client()
        c = client.containers.get(container_id_or_name)
        return "running" if c.status == "running" else "stopped"
    except NotFound:
        return "stopped"
    except Exception:
        return "error"

def get_container_logs(container_id_or_name: str, tail: int = 100) -> str:
    if not container_id_or_name:
        return "No container assigned yet."
    try:
        client = get_docker_client()
        c = client.containers.get(container_id_or_name)
        logs_bytes = c.logs(tail=tail, stdout=True, stderr=True, timestamps=True)
        return logs_bytes.decode("utf-8", errors="ignore")
    except NotFound:
        return "Container not found or stopped."
    except Exception as e:
        return f"Error reading logs: {e}"
