# Curated Marketplace Catalog for SachDeploy v2.0 Enterprise / Phase 3 Server OS

MARKETPLACE_CATALOG = [
    {
        "id": "n8n",
        "name": "n8n Workflow Automation",
        "category": "Automation & Workflows",
        "icon": "⚡",
        "description": "Powerful self-hosted workflow automation tool with 400+ integrations.",
        "ram_tier": "Medium (~512MB)",
        "image": "n8nio/n8n:latest",
        "default_port": 5678,
        "container_port": 5678,
        "env": {
            "N8N_PORT": "5678",
            "N8N_ENCRYPTION_KEY": "sachdeploy_secret_key_12345",
            "WEBHOOK_URL": "http://localhost:5678/"
        },
        "volumes": ["n8n_data:/home/node/.n8n"]
    },
    {
        "id": "portainer",
        "name": "Portainer CE",
        "category": "DevOps & Management",
        "icon": "🐳",
        "description": "Lightweight container management UI for inspecting Docker environments.",
        "ram_tier": "Low (<128MB)",
        "image": "portainer/portainer-ce:latest",
        "default_port": 9000,
        "container_port": 9000,
        "env": {},
        "volumes": [
            "/var/run/docker.sock:/var/run/docker.sock",
            "portainer_data:/data"
        ]
    },
    {
        "id": "postgresql",
        "name": "PostgreSQL 16",
        "category": "Databases & Storage",
        "icon": "🐘",
        "description": "The world's most advanced open-source relational database engine.",
        "ram_tier": "Medium (~256MB)",
        "image": "postgres:16-alpine",
        "default_port": 5432,
        "container_port": 5432,
        "env": {
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "sachpassword123",
            "POSTGRES_DB": "sachdb"
        },
        "volumes": ["pg_data:/var/lib/postgresql/data"]
    },
    {
        "id": "mysql",
        "name": "MySQL 8.0",
        "category": "Databases & Storage",
        "icon": "🐬",
        "description": "Industry standard open-source relational database management system.",
        "ram_tier": "Medium (~384MB)",
        "image": "mysql:8.0",
        "default_port": 3306,
        "container_port": 3306,
        "env": {
            "MYSQL_ROOT_PASSWORD": "sachpassword123",
            "MYSQL_DATABASE": "sachdb"
        },
        "volumes": ["mysql_data:/var/lib/mysql"]
    },
    {
        "id": "redis",
        "name": "Redis 7 Cache",
        "category": "Databases & Storage",
        "icon": "⚡",
        "description": "Ultra-fast in-memory data structure store used as a database, cache, and message broker.",
        "ram_tier": "Low (<64MB)",
        "image": "redis:7-alpine",
        "default_port": 6379,
        "container_port": 6379,
        "env": {},
        "volumes": ["redis_data:/data"]
    },
    {
        "id": "mongodb",
        "name": "MongoDB 7.0",
        "category": "Databases & Storage",
        "icon": "🍃",
        "description": "Flexible NoSQL document database built for scalable modern web applications.",
        "ram_tier": "Medium (~384MB)",
        "image": "mongo:7.0",
        "default_port": 27017,
        "container_port": 27017,
        "env": {
            "MONGO_INITDB_ROOT_USERNAME": "admin",
            "MONGO_INITDB_ROOT_PASSWORD": "sachpassword123"
        },
        "volumes": ["mongo_data:/data/db"]
    },
    {
        "id": "grafana",
        "name": "Grafana Observability",
        "category": "Observability & Monitoring",
        "icon": "📊",
        "description": "Operational dashboards and data visualization platform for monitoring server health.",
        "ram_tier": "Low (<128MB)",
        "image": "grafana/grafana:latest",
        "default_port": 3000,
        "container_port": 3000,
        "env": {
            "GF_SECURITY_ADMIN_PASSWORD": "sachpassword123"
        },
        "volumes": ["grafana_data:/var/lib/grafana"]
    },
    {
        "id": "prometheus",
        "name": "Prometheus Metrics",
        "category": "Observability & Monitoring",
        "icon": "🔥",
        "description": "Systems and service monitoring system with real-time time-series scraping.",
        "ram_tier": "Low (<128MB)",
        "image": "prom/prometheus:latest",
        "default_port": 9090,
        "container_port": 9090,
        "env": {},
        "volumes": ["prom_data:/prometheus"]
    },
    {
        "id": "ollama",
        "name": "Ollama Local AI",
        "category": "Local AI & LLMs",
        "icon": "🤖",
        "description": "Run open-source LLMs (Llama 3, Mistral, Gemma) locally on your own server hardware.",
        "ram_tier": "High (>1GB)",
        "image": "ollama/ollama:latest",
        "default_port": 11434,
        "container_port": 11434,
        "env": {},
        "volumes": ["ollama_data:/root/.ollama"]
    },
    {
        "id": "open-webui",
        "name": "Open WebUI",
        "category": "Local AI & LLMs",
        "icon": "💬",
        "description": "User-friendly ChatGPT-style interface for local Ollama models and AI assistants.",
        "ram_tier": "Medium (~384MB)",
        "image": "ghcr.io/open-webui/open-webui:main",
        "default_port": 8080,
        "container_port": 8080,
        "env": {
            "OLLAMA_BASE_URL": "http://host.docker.internal:11434"
        },
        "volumes": ["open_webui_data:/app/backend/data"]
    },
    {
        "id": "minio",
        "name": "MinIO S3 Storage",
        "category": "Databases & Storage",
        "icon": "🪣",
        "description": "High-performance S3-compatible object storage server for cloud files and backups.",
        "ram_tier": "Medium (~256MB)",
        "image": "minio/minio:latest",
        "default_port": 9001,
        "container_port": 9001,
        "env": {
            "MINIO_ROOT_USER": "admin",
            "MINIO_ROOT_PASSWORD": "sachpassword123"
        },
        "command": "server /data --console-address :9001",
        "volumes": ["minio_data:/data"]
    },
    {
        "id": "gitea",
        "name": "Gitea Git Server",
        "category": "DevOps & Management",
        "icon": "☕",
        "description": "Painless self-hosted Git service inspired by GitHub, lightweight and blazing fast.",
        "ram_tier": "Low (<128MB)",
        "image": "gitea/gitea:latest",
        "default_port": 3001,
        "container_port": 3000,
        "env": {
            "USER_UID": "1000",
            "USER_GID": "1000"
        },
        "volumes": ["gitea_data:/data"]
    },
    {
        "id": "uptime-kuma",
        "name": "Uptime Kuma",
        "category": "Observability & Monitoring",
        "icon": "⏱️",
        "description": "Self-hosted monitoring tool with status pages, SLA tracking, and webhook alerts.",
        "ram_tier": "Low (<128MB)",
        "image": "louislam/uptime-kuma:1",
        "default_port": 3002,
        "container_port": 3001,
        "env": {},
        "volumes": [
            "/var/run/docker.sock:/var/run/docker.sock",
            "kuma_data:/app/data"
        ]
    },
    {
        "id": "nextcloud",
        "name": "Nextcloud Hub",
        "category": "Databases & Storage",
        "icon": "☁️",
        "description": "Self-hosted cloud file collaboration, document editing, photo backup, and sharing platform.",
        "ram_tier": "High (>512MB)",
        "image": "nextcloud:latest",
        "default_port": 8081,
        "container_port": 80,
        "env": {},
        "volumes": ["nextcloud_data:/var/www/html"]
    }
]

def get_catalog():
    return MARKETPLACE_CATALOG

def get_template_by_id(template_id: str):
    for t in MARKETPLACE_CATALOG:
        if t["id"] == template_id:
            return t
    return None
