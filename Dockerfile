FROM python:3.10-slim

WORKDIR /app

# Install git and build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install lightweight Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and templates
COPY backend ./backend
COPY frontend ./frontend
COPY docker ./docker

# Create storage directories
RUN mkdir -p /app/storage/uploads /app/storage/projects

EXPOSE 7000

ENV PORT=7000
ENV STORAGE_PATH=/app/storage
ENV PYTHONPATH=/app

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7000"]
