# SachDeploy v1 (Stable Edition) 🚀

**SachDeploy** is a lightweight, self-hosted deployment platform inspired by Vercel and Railway. Tailored specifically for low-resource Ubuntu servers (**2GB RAM laptops or VPS**), it allows you to deploy and manage Docker-based applications (Python, Node.js, and Static HTML sites) from ZIP uploads or GitHub repositories with zero configuration, accessible seamlessly across your **Tailscale network**.

---

## ✨ Why Stable Edition?

- **🛡️ Built-in System Guard Service (`backend/guard.py`)**:
  - **RAM Guard**: Monitors system memory every 5 seconds. If RAM exceeds **85%**, it automatically emergency-stops the lowest priority container to prevent server OS crashes.
  - **CPU & Disk Guard**: Monitors CPU load (>90%) and automatically cleans/prunes dangling Docker build caches and logs when disk usage exceeds **90%**.
- **🔁 Auto Recovery Engine (`backend/recovery.py`)**:
  - Whenever your server reboots or Docker restarts, SachDeploy reads SQLite state and automatically re-launches all previously running containers with their exact port mappings!
- **📡 Real-Time WebSocket Telemetry (`/ws/events`)**:
  - Streams live CPU %, RAM MB, Disk %, and deployment progress directly to the frontend dashboard without requiring manual page reloads.
- **⚡ Zero Build-Tool Frontend**: Built with pure HTML5, Tailwind CSS CDN, and vanilla JavaScript—no React build pipelines, no Node.js bundling overhead, and instant page loading.
- **🧠 Reliable Auto-Detection**: Inspects uploaded ZIP files or Git repos and applies solid predefined Docker templates:
  - **Python**: Detects `requirements.txt` → runs `uvicorn` / `fastapi` / `flask` / scripts on port `8000`.
  - **Node.js**: Detects `package.json` → runs `npm install && npm start` on port `3000`.
  - **Static Web Sites**: Detects `index.html` → serves via lightweight Nginx Alpine on port `80`.
- **🔌 Automatic Port Management**: Uses a clean, fixed port range (**`8001–8100`**), tracking assignments in embedded SQLite.
- **🛡️ Hardened Resource Guardrails**:
  - **Memory Limit**: Strictly enforces `512MB` RAM maximum per container.
  - **CPU Limit**: Enforces `0.5 core` maximum per container (`50,000` CPU quota).
  - **Active App Cap**: Prevents server OOM crashes by capping concurrent running apps at **3 active applications** (safe for 2GB RAM!).
- **📜 Live Log Streaming**: Instantly inspect the last 100 lines of container console output (`stdout`/`stderr`) in a dark monospace terminal viewer.
- **🔐 Session Token Auth**: Simple, secure session-based authentication stored in SQLite without bloated dependency trees.

---

## 🏗️ Project Structure

```text
SachDeploy/
├── backend/
│   ├── __init__.py           # Package init
│   ├── main.py               # FastAPI server, CORS, WebSocket hub & static serving
│   ├── docker_manager.py     # Docker SDK daemon controls & resource guardrails
│   ├── auth.py               # Session-based authentication & bearer guards
│   ├── db.py                 # SQLite database initialization & CRUD models
│   ├── deploy.py             # Auto-detection engine & ZIP/Git deployment tasks
│   ├── guard.py              # System Guard real-time RAM/CPU/Disk watchdog
│   └── recovery.py           # Auto Recovery startup restoration loop
│
├── frontend/
│   └── index.html            # Standalone Vanilla HTML/JS minimal dark dashboard with WebSocket
│
├── storage/                  # Persistent SQLite DB, uploaded archives, and repos
│   ├── uploads/
│   ├── projects/
│   └── db.sqlite
│
├── docker/
│   ├── python.Dockerfile     # Predefined Python 3.10 slim template
│   ├── node.Dockerfile       # Predefined Node 18 Alpine template
│   └── static.Dockerfile     # Predefined Nginx Alpine template
│
├── Dockerfile                # Root build instructions for SachDeploy platform
├── docker-compose.yml        # Docker Compose multi-service definition
├── requirements.txt          # Lightweight Python dependencies
└── README.md                 # Documentation & installation guide
```

---

## 🛠️ Step-by-Step Installation Guide (Ubuntu Server)

### Step 1: Install Prerequisites on your Server
Ensure your Ubuntu server has Docker and Git installed:

```bash
# Update repositories and install essential utilities
sudo apt update && sudo apt install -y curl git unzip

# Install Docker Engine & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker version
docker --version
docker compose version
```

### Step 2: Clone SachDeploy
```bash
cd ~
git clone https://github.com/codewithsachin10/SachDeploy.git
cd SachDeploy

# Create environment configuration
cp .env.example .env
```

*(Optional)* You can customize your admin credentials by editing `.env` or changing `docker-compose.yml`:
```bash
nano .env
```
*Default Credentials:*
- **Username**: `admin`
- **Password**: `sachdeploy`

### Step 3: Launch Platform Engine
Start the deployment platform using Docker Compose:

```bash
docker compose up -d --build
```

Verify that the `sachdeploy` service is up and running:
```bash
docker ps
```
You will see `sachdeploy` active and listening on port `7000`.

---

## 🌐 How to Access via Tailscale

1. Find your server's Tailscale IP address:
   ```bash
   tailscale ip -4
   ```
   *(Example output: `100.85.120.45`)*

2. Open your web browser on any device connected to your Tailscale network and navigate to:
   ```http
   http://100.85.120.45:7000
   ```

3. Sign in with your configured credentials (`admin` / `sachdeploy`).

---

## 📦 Example Deployments

### 1. Deploying a FastAPI / Python App via ZIP Upload
1. In the top right of your dashboard, click **`+ Deploy New Project`**.
2. Select **`📁 ZIP Upload`**.
3. Enter a project name (e.g., `my-fastapi-service`).
4. Select your `.zip` archive (ensure it contains a `requirements.txt` file at the root).
5. Click **`🚀 Deploy ZIP`**.
6. SachDeploy extracts the archive, copies `docker/python.Dockerfile`, builds the image, and launches the container on the next free port (e.g., `8001`) with a strict 512MB RAM cap!

### 2. Deploying a Node.js App from GitHub
1. Click **`+ Deploy New Project`** -> **`🐙 GitHub Repo`**.
2. Enter a project name (e.g., `express-api`).
3. Paste the repository URL (e.g., `https://github.com/username/express-app.git`).
4. Enter the branch name (`main`).
5. Click **`🚀 Deploy Repo`**. SachDeploy clones the repository, detects `package.json`, and deploys using `docker/node.Dockerfile`!

### 3. Deploying a Static Portfolio Site
1. Upload a ZIP containing an `index.html` file.
2. SachDeploy detects the HTML root, copies `docker/static.Dockerfile`, and serves your site with high-performance Nginx Alpine on the next assigned port!

---

## 🔧 Useful Management Commands

```bash
# View live platform engine logs
docker logs -f sachdeploy

# Restart SachDeploy platform
docker compose restart

# Stop platform service
docker compose down

# Check SQLite database manually
sqlite3 storage/db.sqlite "SELECT name, type, port, status FROM projects;"
```

---
*Built for rock-solid stability and speed on low-resource home servers.*
