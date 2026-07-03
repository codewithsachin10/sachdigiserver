import os
import uuid
import shutil
import asyncio
from typing import Optional, List
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends, UploadFile, File, Form, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.db import (
    init_db, get_all_projects, get_project, get_project_by_name,
    create_project_db, update_project_status, delete_project_db,
    get_notifications, mark_notifications_read, clear_notifications,
    get_all_settings, set_setting, get_project_env, set_project_env, get_deploy_history
)
from backend.auth import authenticate_user, get_current_user
from backend.docker_manager import (
    find_next_free_port, check_active_apps_limit, start_container,
    stop_container, restart_container, remove_container_and_image,
    get_container_status, get_container_logs
)
from backend.deploy import get_storage_dirs, extract_zip, clone_repo, detect_project_type_and_template, deploy_project_background
from backend.guard import SystemGuard
from backend.recovery import auto_recover_apps
from backend.telemetry import get_system_telemetry
import backend.portainer_service as portainer
import backend.file_service as file_mgr
import backend.backup_service as backup_svc
import backend.server_control as sys_ctrl

app = FastAPI(title="SachDeploy v2.0 Enterprise", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

ws_manager = ConnectionManager()
guard_service = SystemGuard(ws_manager)

class LoginRequest(BaseModel):
    username: str
    password: str

class GitDeployRequest(BaseModel):
    name: str
    git_url: str
    branch: Optional[str] = "main"

class SettingItem(BaseModel):
    key: str
    value: str

class ContainerActionRequest(BaseModel):
    action: str
    new_name: Optional[str] = None

class ImagePullRequest(BaseModel):
    image_name: str

class VolumeCreateRequest(BaseModel):
    name: str

class NetworkCreateRequest(BaseModel):
    name: str
    driver: Optional[str] = "bridge"

class FileWriteRequest(BaseModel):
    path: str
    content: str

class FolderCreateRequest(BaseModel):
    path: str

class RenameRequest(BaseModel):
    old_path: str
    new_name: str

class DeleteFileRequest(BaseModel):
    path: str

class RestoreBackupRequest(BaseModel):
    filename: str

class ServerActionRequest(BaseModel):
    action: str

class ProjectEnvRequest(BaseModel):
    env: dict

@app.on_event("startup")
async def startup():
    print("[SachDeploy v2.0] 🚀 Initializing Enterprise Cloud Management Engine...")
    get_storage_dirs()
    init_db()
    
    # Run Auto Recovery
    try:
        auto_recover_apps()
    except Exception as e:
        print(f"[SachDeploy v2.0] Auto recovery notice: {e}")
        
    # Start System Guard loop
    asyncio.create_task(guard_service.start())
    
    # Start Telemetry live broadcast loop (every 5s)
    async def telemetry_loop():
        while True:
            await asyncio.sleep(5)
            if ws_manager.active_connections:
                try:
                    data = get_system_telemetry()
                    await ws_manager.broadcast({"type": "telemetry", "data": data})
                except Exception:
                    pass
    asyncio.create_task(telemetry_loop())
    
    print("[SachDeploy v2.0] All systems online! Ready on port 7000.")

@app.on_event("shutdown")
def shutdown():
    guard_service.stop()

# --- WebSocket Endpoint ---
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial telemetry immediately upon connection
        data = get_system_telemetry()
        await websocket.send_json({"type": "telemetry", "data": data})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# --- Auth Routes ---
@app.post("/api/login")
async def login(req: LoginRequest, response: Response):
    res = authenticate_user(req.username, req.password)
    if not res:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    response.set_cookie(key="sach_session", value=res["token"], httponly=False, max_age=86400 * 7)
    return res

@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie("sach_session")
    return {"message": "Logged out successfully"}

@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"username": user["username"]}

# --- Telemetry & Notifications Routes ---
@app.get("/api/telemetry")
async def get_telemetry(user: dict = Depends(get_current_user)):
    return get_system_telemetry()

@app.get("/api/notifications")
async def get_notifs(user: dict = Depends(get_current_user)):
    return get_notifications()

@app.post("/api/notifications/read")
async def read_notifs(user: dict = Depends(get_current_user)):
    mark_notifications_read()
    return {"status": "success"}

@app.delete("/api/notifications")
async def clear_notifs(user: dict = Depends(get_current_user)):
    clear_notifications()
    return {"status": "success"}

@app.get("/api/settings")
async def list_settings(user: dict = Depends(get_current_user)):
    return get_all_settings()

@app.post("/api/settings")
async def update_setting(item: SettingItem, user: dict = Depends(get_current_user)):
    set_setting(item.key, item.value)
    await ws_manager.broadcast({"type": "settings_update"})
    return {"status": "success"}

# --- Project Routes ---
@app.get("/api/projects")
async def list_projects(user: dict = Depends(get_current_user)):
    projects = get_all_projects()
    for p in projects:
        if p.get("container_id") and not p.get("status", "").startswith("error") and p.get("status") != "building":
            live_status = get_container_status(p["container_id"])
            if live_status != p["status"]:
                update_project_status(p["id"], live_status)
                p["status"] = live_status
    return projects

@app.get("/api/projects/{project_id}")
async def get_single_project(project_id: str, user: dict = Depends(get_current_user)):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@app.get("/api/projects/{project_id}/env")
async def get_proj_env(project_id: str, user: dict = Depends(get_current_user)):
    return get_project_env(project_id)

@app.post("/api/projects/{project_id}/env")
async def set_proj_env(project_id: str, req: ProjectEnvRequest, user: dict = Depends(get_current_user)):
    set_project_env(project_id, req.env)
    return {"status": "success"}

@app.get("/api/projects/{project_id}/history")
async def get_proj_history(project_id: str, user: dict = Depends(get_current_user)):
    return get_deploy_history(project_id)

@app.post("/api/deploy/zip")
async def deploy_zip(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    clean_name = name.strip().lower().replace(" ", "-")
    if get_project_by_name(clean_name):
        raise HTTPException(status_code=400, detail="Project with this name already exists")
        
    check_active_apps_limit()
    
    uploads_dir, projects_dir = get_storage_dirs()
    project_id = f"sach-{uuid.uuid4().hex[:6]}"
    
    zip_path = os.path.join(uploads_dir, f"{project_id}.zip")
    with open(zip_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    project_dir = os.path.join(projects_dir, clean_name)
    extract_zip(zip_path, project_dir)
    
    try:
        proj_type, internal_port, _ = detect_project_type_and_template(project_dir)
    except Exception as e:
        shutil.rmtree(project_dir, ignore_errors=True)
        try: os.remove(zip_path)
        except: pass
        raise HTTPException(status_code=400, detail=str(e))
        
    host_port = find_next_free_port()
    image_name = f"sachdeploy-{clean_name}:latest"
    
    project_data = {
        "id": project_id,
        "name": clean_name,
        "type": proj_type,
        "source": "zip",
        "port": host_port,
        "internal_port": internal_port,
        "image_name": image_name,
        "status": "building"
    }
    created = create_project_db(project_data)
    
    async def run_deploy():
        await deploy_project_background(project_id, clean_name, project_dir, image_name, host_port, ws_manager, user["username"])
        
    background_tasks.add_task(run_deploy)
    await ws_manager.broadcast({"type": "status_update"})
    return created

@app.post("/api/deploy/git")
async def deploy_git(
    req: GitDeployRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    clean_name = req.name.strip().lower().replace(" ", "-")
    if get_project_by_name(clean_name):
        raise HTTPException(status_code=400, detail="Project with this name already exists")
        
    check_active_apps_limit()
    
    _, projects_dir = get_storage_dirs()
    project_id = f"sach-{uuid.uuid4().hex[:6]}"
    project_dir = os.path.join(projects_dir, clean_name)
    
    host_port = find_next_free_port()
    image_name = f"sachdeploy-{clean_name}:latest"
    
    project_data = {
        "id": project_id,
        "name": clean_name,
        "type": "git-detecting",
        "source": req.git_url,
        "port": host_port,
        "internal_port": 8000,
        "image_name": image_name,
        "status": "building"
    }
    created = create_project_db(project_data)
    
    async def clone_and_deploy():
        try:
            clone_repo(req.git_url, req.branch, project_dir)
            proj_type, internal_port, _ = detect_project_type_and_template(project_dir)
            
            from backend.db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET type = ?, internal_port = ? WHERE id = ?", (proj_type, internal_port, project_id))
            conn.commit()
            conn.close()
            
            await deploy_project_background(project_id, clean_name, project_dir, image_name, host_port, ws_manager, user["username"])
        except Exception as e:
            update_project_status(project_id, f"error: {str(e)[:40]}")
            await ws_manager.broadcast({"type": "status_update"})
            
    background_tasks.add_task(clone_and_deploy)
    await ws_manager.broadcast({"type": "status_update"})
    return created

@app.post("/api/projects/{project_id}/start")
async def start_app(project_id: str, user: dict = Depends(get_current_user)):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        start_container(p.get("container_id") or f"app-{p['name']}")
        update_project_status(project_id, "running")
        await ws_manager.broadcast({"type": "status_update"})
        return {"status": "running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_id}/stop")
async def stop_app(project_id: str, user: dict = Depends(get_current_user)):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        stop_container(p.get("container_id") or f"app-{p['name']}")
        update_project_status(project_id, "stopped")
        await ws_manager.broadcast({"type": "status_update"})
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_id}/restart")
async def restart_app(project_id: str, user: dict = Depends(get_current_user)):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        restart_container(p.get("container_id") or f"app-{p['name']}")
        update_project_status(project_id, "running")
        await ws_manager.broadcast({"type": "status_update"})
        return {"status": "running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_app(project_id: str, user: dict = Depends(get_current_user)):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
        
    remove_container_and_image(p.get("container_id") or f"app-{p['name']}", p.get("image_name"))
    
    _, projects_dir = get_storage_dirs()
    project_dir = os.path.join(projects_dir, p["name"])
    shutil.rmtree(project_dir, ignore_errors=True)
    
    delete_project_db(project_id)
    await ws_manager.broadcast({"type": "status_update"})
    return {"message": "Project deleted successfully"}

@app.get("/api/projects/{project_id}/logs")
async def get_logs(project_id: str, user: dict = Depends(get_current_user)):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    logs = get_container_logs(p.get("container_id") or f"app-{p['name']}", tail=150)
    return {"logs": logs, "status": p.get("status")}

# --- Portainer Replacement Routes ---
@app.get("/api/docker/containers")
async def get_containers(user: dict = Depends(get_current_user)):
    return portainer.list_all_containers()

@app.post("/api/docker/containers/{container_id}/action")
async def container_action(container_id: str, req: ContainerActionRequest, user: dict = Depends(get_current_user)):
    act = req.action
    try:
        if act == "start":
            start_container(container_id)
        elif act == "stop":
            stop_container(container_id)
        elif act == "restart":
            restart_container(container_id)
        elif act == "delete":
            remove_container_and_image(container_id, None)
        elif act == "duplicate":
            if not req.new_name: raise HTTPException(status_code=400, detail="new_name required")
            res = portainer.duplicate_container(container_id, req.new_name)
            await ws_manager.broadcast({"type": "status_update"})
            return res
        elif act == "rename":
            if not req.new_name: raise HTTPException(status_code=400, detail="new_name required")
            res = portainer.rename_container(container_id, req.new_name)
            await ws_manager.broadcast({"type": "status_update"})
            return res
        else:
            raise HTTPException(status_code=400, detail="Invalid container action")
            
        await ws_manager.broadcast({"type": "status_update"})
        return {"status": "success", "action": act}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/docker/images")
async def get_images(user: dict = Depends(get_current_user)):
    return portainer.list_all_images()

@app.post("/api/docker/images/pull")
async def pull_docker_image(req: ImagePullRequest, user: dict = Depends(get_current_user)):
    try:
        res = portainer.pull_image(req.image_name)
        await ws_manager.broadcast({"type": "status_update"})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/docker/images/{image_id}")
async def delete_docker_image(image_id: str, user: dict = Depends(get_current_user)):
    try:
        res = portainer.remove_image(image_id)
        await ws_manager.broadcast({"type": "status_update"})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/docker/images/prune")
async def prune_docker_images(user: dict = Depends(get_current_user)):
    try:
        res = portainer.prune_images()
        await ws_manager.broadcast({"type": "status_update"})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/docker/volumes")
async def get_volumes(user: dict = Depends(get_current_user)):
    return portainer.list_all_volumes()

@app.post("/api/docker/volumes")
async def create_docker_volume(req: VolumeCreateRequest, user: dict = Depends(get_current_user)):
    try:
        res = portainer.create_volume(req.name)
        await ws_manager.broadcast({"type": "status_update"})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/docker/volumes/{name}")
async def delete_docker_volume(name: str, user: dict = Depends(get_current_user)):
    try:
        res = portainer.remove_volume(name)
        await ws_manager.broadcast({"type": "status_update"})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/docker/volumes/prune")
async def prune_docker_volumes(user: dict = Depends(get_current_user)):
    try:
        res = portainer.prune_volumes()
        await ws_manager.broadcast({"type": "status_update"})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/docker/networks")
async def get_networks(user: dict = Depends(get_current_user)):
    return portainer.list_all_networks()

@app.post("/api/docker/networks")
async def create_docker_network(req: NetworkCreateRequest, user: dict = Depends(get_current_user)):
    try:
        res = portainer.create_network(req.name, req.driver)
        await ws_manager.broadcast({"type": "status_update"})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/docker/networks/{net_id}")
async def delete_docker_network(net_id: str, user: dict = Depends(get_current_user)):
    try:
        res = portainer.remove_network(net_id)
        await ws_manager.broadcast({"type": "status_update"})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- File Manager Routes ---
@app.get("/api/files/list")
async def list_files(path: str = "", user: dict = Depends(get_current_user)):
    return file_mgr.list_directory(path)

@app.get("/api/files/read")
async def read_file(path: str, user: dict = Depends(get_current_user)):
    return file_mgr.read_file_content(path)

@app.post("/api/files/write")
async def write_file(req: FileWriteRequest, user: dict = Depends(get_current_user)):
    return file_mgr.write_file_content(req.path, req.content)

@app.post("/api/files/folder")
async def create_dir(req: FolderCreateRequest, user: dict = Depends(get_current_user)):
    return file_mgr.create_folder(req.path)

@app.post("/api/files/rename")
async def rename_file_item(req: RenameRequest, user: dict = Depends(get_current_user)):
    return file_mgr.rename_item(req.old_path, req.new_name)

@app.delete("/api/files/delete")
async def delete_file_item(path: str, user: dict = Depends(get_current_user)):
    return file_mgr.delete_item(path)

# --- Backup Service Routes ---
@app.get("/api/backups")
async def list_backups(user: dict = Depends(get_current_user)):
    return backup_svc.list_system_backups()

@app.post("/api/backups/create")
async def create_backup(user: dict = Depends(get_current_user)):
    return backup_svc.create_system_backup()

@app.post("/api/backups/restore")
async def restore_backup(req: RestoreBackupRequest, user: dict = Depends(get_current_user)):
    res = backup_svc.restore_system_backup(req.filename)
    await ws_manager.broadcast({"type": "status_update"})
    return res

@app.delete("/api/backups/{filename}")
async def delete_backup(filename: str, user: dict = Depends(get_current_user)):
    return backup_svc.delete_system_backup(filename)

# --- Server Control Routes ---
@app.post("/api/server/action")
async def server_control_action(req: ServerActionRequest, user: dict = Depends(get_current_user)):
    act = req.action
    if act == "restart_service":
        return sys_ctrl.restart_sachdeploy_service()
    elif act == "clear_cache":
        return sys_ctrl.clear_docker_cache()
    elif act == "clean_logs":
        return sys_ctrl.clean_system_logs()
    elif act == "reboot":
        return sys_ctrl.reboot_server()
    elif act == "shutdown":
        return sys_ctrl.shutdown_server()
    else:
        raise HTTPException(status_code=400, detail="Unknown server action")

# --- Static Frontend Serving ---
frontend_path = "/app/frontend" if os.path.exists("/app/frontend") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

@app.get("/")
async def serve_dashboard():
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "SachDeploy v2.0 Enterprise API Running. Frontend index.html not found."})

@app.get("/{filename}")
async def serve_static_file(filename: str):
    file_path = os.path.join(frontend_path, filename)
    if os.path.exists(file_path) and not os.path.isdir(file_path):
        return FileResponse(file_path)
    # SPA fallback or 404
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
