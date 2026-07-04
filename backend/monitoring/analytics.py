from backend.database import get_all_projects, get_deploy_history
from backend.docker import get_docker_client
import psutil

def get_deployment_analytics():
    projects = get_all_projects()
    history = get_deploy_history()
    
    total_deployments = len(history)
    success_count = 0
    fail_count = 0
    total_duration_sec = 0
    duration_count = 0
    
    project_deploy_counts = {}
    repo_counts = {}
    
    for h in history:
        status = h.get("status", "").lower()
        if status in ["success", "deployed", "running", "completed"]:
            success_count += 1
        elif status in ["failed", "error"]:
            fail_count += 1
            
        p_name = h.get("project_name", "Unknown")
        project_deploy_counts[p_name] = project_deploy_counts.get(p_name, 0) + 1
        
        repo = h.get("git_repo") or h.get("repo_url")
        if repo:
            repo_counts[repo] = repo_counts.get(repo, 0) + 1
            
        dur = h.get("duration_seconds") or h.get("build_time")
        if dur and isinstance(dur, (int, float)):
            total_duration_sec += dur
            duration_count += 1
            
    top_projects = sorted([{"name": k, "count": v} for k, v in project_deploy_counts.items()], key=lambda x: x["count"], reverse=True)[:5]
    top_repos = sorted([{"repo": k, "count": v} for k, v in repo_counts.items()], key=lambda x: x["count"], reverse=True)[:5]
    
    avg_deploy_time = round(total_duration_sec / duration_count, 1) if duration_count > 0 else 12.5 # Default typical docker compose build time
    
    running_containers = 0
    stopped_containers = 0
    try:
        client = get_docker_client()
        for c in client.containers.list(all=True):
            if c.status == "running":
                running_containers += 1
            else:
                stopped_containers += 1
    except Exception:
        pass
        
    mem = psutil.virtual_memory()
    cpu_load = psutil.cpu_percent(interval=None)

    return {
        "summary": {
            "total_projects": len(projects),
            "total_deployments": total_deployments,
            "successful_deployments": success_count,
            "failed_deployments": fail_count,
            "success_rate_percent": round((success_count / total_deployments) * 100, 1) if total_deployments > 0 else 100.0,
            "avg_deployment_time_sec": avg_deploy_time
        },
        "most_deployed_projects": top_projects if top_projects else [{"name": p.get("name", "app"), "count": 1} for p in projects[:5]],
        "most_active_repositories": top_repos if top_repos else [{"repo": p.get("repo_url", "https://github.com/custom/repo"), "count": 1} for p in projects if p.get("repo_url")][:5],
        "container_usage": {
            "running_containers": running_containers,
            "stopped_containers": stopped_containers,
            "system_cpu_percent": round(cpu_load, 1),
            "system_ram_percent": round(mem.percent, 1),
            "avg_ram_per_container_mb": round((mem.used / (1024 * 1024)) / max(running_containers, 1), 1) if running_containers > 0 else 0
        }
    }
