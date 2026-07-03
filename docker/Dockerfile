FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend ./backend
COPY frontend ./frontend

# Create storage directories
RUN mkdir -p /app/storage/projects /app/storage/logs /app/storage/uploads

# Expose port 7000
EXPOSE 7000

# Set environment variables
ENV PORT=7000
ENV STORAGE_PATH=/app/storage
ENV PYTHONPATH=/app

# Start Uvicorn server
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7000"]
