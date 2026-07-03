from backend.db import get_all_projects, update_project_status
from backend.docker_manager import get_container_status, start_container, run_container

def auto_recover_apps():
    print("[Auto Recovery] 🔁 Checking deployed application states from SQLite...")
    projects = get_all_projects()
    recovered_count = 0
    
    for p in projects:
        # If project was marked running or we want to restore containers after server reboot
        if p.get("status") == "running" or p.get("status", "").startswith("stopped"):
            c_id = p.get("container_id") or f"app-{p['name']}"
            status = get_container_status(c_id)
            
            if p["status"] == "running" and status != "running":
                print(f"[Auto Recovery] 🔄 Restoring container for project '{p['name']}' on port {p['port']}...")
                try:
                    # Attempt simple container start
                    start_container(c_id)
                    update_project_status(p["id"], "running")
                    recovered_count += 1
                    print(f"[Auto Recovery] ✅ Successfully started '{p['name']}'")
                except Exception as e1:
                    print(f"[Auto Recovery] Container start failed ({e1}). Attempting full container re-launch from image...")
                    try:
                        new_id = run_container(p["image_name"], f"app-{p['name']}", p["port"], p["internal_port"])
                        update_project_status(p["id"], "running", new_id)
                        recovered_count += 1
                        print(f"[Auto Recovery] ✅ Successfully re-launched '{p['name']}' container ({new_id[:8]})")
                    except Exception as e2:
                        print(f"[Auto Recovery] ❌ Could not recover '{p['name']}': {e2}")
                        update_project_status(p["id"], "stopped")
                        
    print(f"[Auto Recovery] 🏁 Recovery complete. Restored {recovered_count} application(s).")
