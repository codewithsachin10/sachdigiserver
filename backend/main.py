import os
import uuid
import shutil
import asyncio
from typing import Optional, List
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends, UploadFile, File, Form, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.db import init_db, get_all_projects, get_project, get_project_by_name, create_project_db, update_project_status, delete_project_db
from backend.auth import authenticate_user, get_current_user
from backend.docker_manager import find_next_free_port, check_active_apps_limit, start_container, stop_container, restart_container, remove_container_and_image, get_container_status, get_container_logs
from backend.deploy import get_storage_dirs, extract_zip, clone_repo, detect_project_type_and_template, deploy_project_background
from backend.guard import SystemGuard
from backend.recovery import auto_recover_apps

app = FastAPI(title="SachDeploy v1 Stable", version="1.0.0")

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

@app.on_event("startup")
async def startup():
    print("[SachDeploy] 🚀 Starting server initialization...")
    get_storage_dirs()
    init_db()
    
    # Run Auto Recovery
    try:
        auto_recover_apps()
    except Exception as e:
        print(f"[SachDeploy] Auto recovery notice: {e}")
        
    # Start System Guard loop
    asyncio.create_task(guard_service.start())
    print("[SachDeploy] Ready! Listening on port 7000.")

@app.on_event("shutdown")
def shutdown():
    guard_service.stop()

# --- WebSocket Endpoint ---
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
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
        deploy_project_background(project_id, clean_name, project_dir, image_name, host_port)
        await ws_manager.broadcast({"type": "status_update"})
        
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
            
            deploy_project_background(project_id, clean_name, project_dir, image_name, host_port)
        except Exception as e:
            update_project_status(project_id, f"error: {str(e)[:40]}")
        finally:
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
    logs = get_container_logs(p.get("container_id") or f"app-{p['name']}", tail=100)
    return {"logs": logs, "status": p.get("status")}

# --- Static Frontend Serving ---
frontend_path = "/app/frontend" if os.path.exists("/app/frontend") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

@app.get("/")
async def serve_dashboard():
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "SachDeploy Stable API Running. Frontend index.html not found."})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
