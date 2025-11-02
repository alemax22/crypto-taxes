# Dev container Dockerfile - extends the backend Dockerfile
# This ensures packages are installed and available in the dev environment

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace/backend

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        git \
        sudo \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with sudo access
RUN useradd --create-home --shell /bin/bash app \
    && echo 'app ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Set working directory (will be overridden by volume mount, but needed for initial setup)
WORKDIR /workspace

# Install Python dependencies from backend requirements
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Create persistent data directory structure
RUN mkdir -p /app/persistent_data/data \
    && mkdir -p /app/persistent_data/logs \
    && mkdir -p /app/persistent_data/config \
    && chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 5000

# Default command (will be overridden by docker-compose)
CMD ["sleep", "infinity"]
