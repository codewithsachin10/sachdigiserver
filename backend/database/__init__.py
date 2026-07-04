from backend.database.connection import get_db_path, get_connection
from backend.database.models import hash_password, init_db
from backend.database.queries import (
    verify_user,
    set_session_token,
    get_user_by_token,
    get_all_projects,
    get_project,
    get_project_by_name,
    create_project_db,
    update_project_status,
    delete_project_db,
    add_notification,
    get_notifications,
    mark_notifications_read,
    clear_notifications,
    add_deploy_history,
    get_deploy_history,
    get_setting,
    set_setting,
    get_all_settings,
    get_project_env,
    set_project_env,
    get_active_apps_count
)
