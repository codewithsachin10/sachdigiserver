FROM python:3.10-slim

WORKDIR /app

# Install git, Docker CLI, and full system DevOps utilities for Integrated Terminal
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    build-essential \
    docker.io \
    procps \
    htop \
    iproute2 \
    iputils-ping \
    net-tools \
    vim \
    nano \
    zip \
    unzip \
    jq \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install lightweight Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and templates
COPY backend ./backend
COPY frontend ./frontend
COPY docker ./docker
COPY audit_imports.py ./audit_imports.py

# Create storage directories and host mount point
RUN mkdir -p /app/storage/uploads /app/storage/projects /host_root

# Run automated import verification audit during build
ENV PYTHONPATH=/app
RUN python audit_imports.py

EXPOSE 7000

ENV PORT=7000
ENV STORAGE_PATH=/app/storage
ENV PYTHONPATH=/app
ENV TERM=xterm-256color

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7000"]
