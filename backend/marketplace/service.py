import uuid
import docker
import asyncio
from typing import Dict, Any, List
from backend.marketplace.catalog import get_template_by_id
from backend.database import create_project_db, update_project_status, get_setting, get_active_apps_count

try:
    docker_client = docker.from_env()
except Exception:
    docker_client = None

async def deploy_template(
    template_id: str,
    custom_name: str = None,
    custom_port: int = None,
    custom_env: Dict[str, str] = None,
    ws_notify_func = None
) -> Dict[str, Any]:
    if not docker_client:
        raise RuntimeError("Docker daemon is not reachable.")

    template = get_template_by_id(template_id)
    if not template:
        raise ValueError(f"Template ID '{template_id}' not found in Marketplace catalog.")

    # Check RAM/App limits
    max_apps = int(get_setting("max_active_apps", "3"))
    if get_active_apps_count() >= max_apps:
        raise RuntimeError(f"Maximum active applications limit ({max_apps}) reached. Stop an app or increase limit in Settings.")

    app_name = custom_name or template["name"].replace(" ", "-").lower()
    # Clean container name
    clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in app_name)
    host_port = int(custom_port if custom_port is not None else template["default_port"])
    container_port = int(template.get("container_port", host_port))
    
    # Merge default env with custom env
    env_vars = template.get("env", {}).copy()
    if custom_env:
        env_vars.update(custom_env)

    # Register project in SQLite first
    proj_id = str(uuid.uuid4())[:8]
    project_data = {
        "id": proj_id,
        "name": clean_name,
        "type": "marketplace",
        "source": f"{template['id']} ({template['image']})",
        "port": host_port,
        "internal_port": container_port,
        "image_name": template["image"],
        "status": "building"
    }
    create_project_db(project_data)

    if ws_notify_func:
        await ws_notify_func({"type": "notification", "message": f"🛍️ Pulling Docker image: {template['image']}..."})

    try:
        # Step 1: Pull Image
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: docker_client.images.pull(template["image"]))
        
        if ws_notify_func:
            await ws_notify_func({"type": "notification", "message": f"✅ Image pulled! Creating storage volumes..."})

        # Step 2: Create required volumes
        volumes_config = {}
        for vol_str in template.get("volumes", []):
            if ":" in vol_str:
                src, dst = vol_str.split(":", 1)
                # If named volume (not absolute path like /var/run/docker.sock), create it
                if not src.startswith("/"):
                    try:
                        docker_client.volumes.get(src)
                    except docker.errors.NotFound:
                        docker_client.volumes.create(src)
                volumes_config[src] = {"bind": dst, "mode": "rw"}

        # Step 3: Check and remove existing container with same name if any
        try:
            old = docker_client.containers.get(clean_name)
            old.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Step 4: Run container
        if ws_notify_func:
            await ws_notify_func({"type": "notification", "message": f"🚀 Launching container '{clean_name}' on port {host_port}..."})

        port_bindings = {f"{container_port}/tcp": host_port}
        
        run_kwargs = {
            "name": clean_name,
            "detach": True,
            "restart_policy": {"Name": "unless-stopped"},
            "ports": port_bindings,
            "environment": env_vars,
            "volumes": volumes_config
        }
        if template.get("command"):
            run_kwargs["command"] = template["command"]

        # Apply RAM limit if configured (e.g. 512m)
        max_ram = get_setting("max_ram_mb", "512")
        if max_ram and max_ram.isdigit():
            if "High" in template["ram_tier"] and int(max_ram) < 1024:
                run_kwargs["mem_limit"] = "1024m"
            else:
                run_kwargs["mem_limit"] = f"{max_ram}m"

        container = docker_client.containers.run(template["image"], **run_kwargs)
        
        update_project_status(proj_id, "running", container_id=container.id)
        if ws_notify_func:
            await ws_notify_func({"type": "notification", "message": f"🎉 Deployed '{clean_name}' successfully on port {host_port}!"})
            await ws_notify_func({"type": "status_update"})

        return {
            "project_id": proj_id,
            "container_id": container.id,
            "name": clean_name,
            "port": host_port,
            "status": "running"
        }

    except Exception as e:
        update_project_status(proj_id, "stopped")
        if ws_notify_func:
            await ws_notify_func({"type": "notification", "message": f"❌ Marketplace deploy failed: {str(e)}"})
        raise e
