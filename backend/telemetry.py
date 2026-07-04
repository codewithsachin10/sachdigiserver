# Backward compatibility wrapper for SachDeploy telemetry service
from backend.monitoring import (
    get_os_info,
    get_tailscale_ip,
    get_tailscale_status,
    get_internet_status,
    get_cpu_temp,
    get_system_telemetry
)
