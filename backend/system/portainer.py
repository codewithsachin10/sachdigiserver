import docker
from docker.errors import NotFound, APIError
from backend.docker import get_docker_client

# --- Containers API ---
def list_all_containers():
    client = get_docker_client()
    containers = client.containers.list(all=True)
    results = []
    for c in containers:
        ports = []
        for int_p, bindings in (c.ports or {}).items():
            if bindings:
                for b in bindings:
                    ports.append(f"{b.get('HostIp', '')}:{b.get('HostPort', '')}->{int_p}")
            else:
                ports.append(int_p)
                
        results.append({
            "id": c.short_id,
            "full_id": c.id,
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.attrs.get("Config", {}).get("Image", "unknown"),
            "status": c.status,
            "state": c.attrs.get("State", {}).get("Status", c.status),
            "created": c.attrs.get("Created", "").split(".")[0].replace("T", " "),
            "ports": ports
        })
    return results

def get_container_inspect(container_id: str):
    client = get_docker_client()
    try:
        c = client.containers.get(container_id)
        return c.attrs
    except NotFound:
        return {"error": "Container not found"}

def duplicate_container(container_id: str, new_name: str):
    client = get_docker_client()
    try:
        c = client.containers.get(container_id)
        config = c.attrs.get("Config", {})
        host_config = c.attrs.get("HostConfig", {})
        image = config.get("Image")
        
        # Launch duplicate with same image and basic limits
        new_c = client.containers.run(
            image=image,
            name=new_name,
            detach=True,
            mem_limit=host_config.get("Memory", 536870912),
            cpu_quota=host_config.get("CpuQuota", 50000)
        )
        return {"status": "success", "id": new_c.short_id, "name": new_name}
    except Exception as e:
        raise RuntimeError(f"Duplicate container failed: {e}")

def rename_container(container_id: str, new_name: str):
    client = get_docker_client()
    try:
        c = client.containers.get(container_id)
        c.rename(new_name)
        return {"status": "success", "new_name": new_name}
    except Exception as e:
        raise RuntimeError(f"Rename failed: {e}")

# --- Images API ---
def list_all_images():
    client = get_docker_client()
    images = client.images.list(all=False)
    results = []
    for img in images:
        size_mb = round((img.attrs.get("Size", 0) or 0) / (1024 * 1024), 1)
        tags = img.tags if img.tags else ["<none>:<none>"]
        results.append({
            "id": img.short_id.replace("sha256:", ""),
            "tags": tags,
            "size_mb": size_mb,
            "created": img.attrs.get("Created", "").split("T")[0]
        })
    return results

def pull_image(image_name: str):
    client = get_docker_client()
    try:
        client.images.pull(image_name)
        return {"status": "success", "image": image_name}
    except Exception as e:
        raise RuntimeError(f"Failed to pull image '{image_name}': {e}")

def remove_image(image_id: str, force: bool = True):
    client = get_docker_client()
    try:
        client.images.remove(image=image_id, force=force)
        return {"status": "success"}
    except Exception as e:
        raise RuntimeError(f"Failed to remove image: {e}")

def prune_images():
    client = get_docker_client()
    try:
        res = client.images.prune(filters={"dangling": True})
        return {"status": "success", "reclaimed_bytes": res.get("SpaceReclaimed", 0)}
    except Exception as e:
        raise RuntimeError(f"Prune images failed: {e}")

# --- Volumes API ---
def list_all_volumes():
    client = get_docker_client()
    volumes = client.volumes.list()
    results = []
    for v in volumes:
        results.append({
            "name": v.name,
            "driver": v.attrs.get("Driver", "local"),
            "mountpoint": v.attrs.get("Mountpoint", ""),
            "created": v.attrs.get("CreatedAt", "").split("T")[0] if v.attrs.get("CreatedAt") else "N/A"
        })
    return results

def create_volume(name: str):
    client = get_docker_client()
    try:
        v = client.volumes.create(name=name, driver="local")
        return {"status": "success", "name": v.name}
    except Exception as e:
        raise RuntimeError(f"Volume creation failed: {e}")

def remove_volume(name: str):
    client = get_docker_client()
    try:
        v = client.volumes.get(name)
        v.remove(force=True)
        return {"status": "success"}
    except Exception as e:
        raise RuntimeError(f"Volume removal failed: {e}")

def prune_volumes():
    client = get_docker_client()
    try:
        res = client.volumes.prune()
        return {"status": "success", "reclaimed_bytes": res.get("SpaceReclaimed", 0)}
    except Exception as e:
        raise RuntimeError(f"Prune volumes failed: {e}")

# --- Networks API ---
def list_all_networks():
    client = get_docker_client()
    networks = client.networks.list()
    results = []
    for net in networks:
        containers_count = len(net.attrs.get("Containers", {}) or {})
        results.append({
            "id": net.short_id,
            "name": net.name,
            "driver": net.attrs.get("Driver", "bridge"),
            "scope": net.attrs.get("Scope", "local"),
            "containers_count": containers_count
        })
    return results

def create_network(name: str, driver: str = "bridge"):
    client = get_docker_client()
    try:
        net = client.networks.create(name=name, driver=driver)
        return {"status": "success", "id": net.short_id, "name": net.name}
    except Exception as e:
        raise RuntimeError(f"Network creation failed: {e}")

def remove_network(net_id_or_name: str):
    client = get_docker_client()
    try:
        net = client.networks.get(net_id_or_name)
        net.remove()
        return {"status": "success"}
    except Exception as e:
        raise RuntimeError(f"Network removal failed: {e}")
