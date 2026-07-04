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
        "name": "Grafana Analytics",
        "category": "Monitoring & Observability",
        "icon": "📊",
        "description": "Operational dashboards and data visualization platform for monitoring telemetry.",
        "ram_tier": "Medium (~256MB)",
        "image": "grafana/grafana:latest",
        "default_port": 3001,
        "container_port": 3000,
        "env": {
            "GF_SECURITY_ADMIN_PASSWORD": "sachpassword123"
        },
        "volumes": ["grafana_data:/var/lib/grafana"]
    },
    {
        "id": "prometheus",
        "name": "Prometheus Monitoring",
        "category": "Monitoring & Observability",
        "icon": "🔥",
        "description": "Systems monitoring and alerting toolkit with time-series database.",
        "ram_tier": "Medium (~256MB)",
        "image": "prom/prometheus:latest",
        "default_port": 9090,
        "container_port": 9090,
        "env": {},
        "volumes": ["prom_data:/prometheus"]
    },
    {
        "id": "ollama",
        "name": "Ollama AI Engine",
        "category": "AI & Machine Learning",
        "icon": "🦙",
        "description": "Run open-source large language models locally (Llama 3, Mistral, Phi-3).",
        "ram_tier": "High (>1GB)",
        "image": "ollama/ollama:latest",
        "default_port": 11434,
        "container_port": 11434,
        "env": {},
        "volumes": ["ollama_data:/root/.ollama"]
    },
    {
        "id": "openwebui",
        "name": "Open WebUI for AI",
        "category": "AI & Machine Learning",
        "icon": "🤖",
        "description": "User-friendly ChatGPT-style interface for local Ollama LLM models.",
        "ram_tier": "Medium (~384MB)",
        "image": "ghcr.io/open-webui/open-webui:main",
        "default_port": 3002,
        "container_port": 8080,
        "env": {
            "OLLAMA_BASE_URL": "http://172.17.0.1:11434"
        },
        "volumes": ["openwebui_data:/app/backend/data"]
    },
    {
        "id": "minio",
        "name": "MinIO Object Storage",
        "category": "Databases & Storage",
        "icon": "🪣",
        "description": "High-performance S3-compatible cloud storage server for data storage.",
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
        "name": "Gitea Git Service",
        "category": "DevOps & Management",
        "icon": "☕",
        "description": "Painless self-hosted Git service and code repository collaboration platform.",
        "ram_tier": "Medium (~256MB)",
        "image": "gitea/gitea:latest",
        "default_port": 3003,
        "container_port": 3000,
        "env": {},
        "volumes": ["gitea_data:/data"]
    },
    {
        "id": "uptimekuma",
        "name": "Uptime Kuma",
        "category": "Monitoring & Observability",
        "icon": "🐻",
        "description": "Self-hosted monitoring tool for HTTP, TCP, Ping, and DNS services with status pages.",
        "ram_tier": "Low (<128MB)",
        "image": "louislam/uptime-kuma:1",
        "default_port": 3004,
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
