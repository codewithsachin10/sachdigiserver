# Backward compatibility wrapper for SachDeploy Portainer management service
from backend.system import (
    list_all_containers,
    get_container_inspect,
    duplicate_container,
    rename_container,
    list_all_images,
    pull_image,
    remove_image,
    prune_images,
    list_all_volumes,
    create_volume,
    remove_volume,
    prune_volumes,
    list_all_networks,
    create_network,
    remove_network
)
