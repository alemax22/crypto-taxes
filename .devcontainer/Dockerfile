# Dev container Dockerfile - includes all development tools
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace/backend
ENV NODE_VERSION=18

# Install system dependencies and development tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    git \
    sudo \
    wget \
    vim \
    nano \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (for frontend development)
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with sudo access
RUN useradd --create-home --shell /bin/bash app \
    && echo 'app ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Set working directory
WORKDIR /workspace

# Install Python dependencies from backend requirements
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir pytest pytest-cov black isort \
    && rm /tmp/requirements.txt

# Install global Node.js tools (optional, for frontend development)
RUN npm install -g npm@latest

# Create persistent data directory structure
RUN mkdir -p /app/persistent_data/data \
    && mkdir -p /app/persistent_data/logs \
    && mkdir -p /app/persistent_data/config \
    && chown -R app:app /app

# Switch to non-root user
USER app

# Default command (will be overridden by docker-compose)
CMD ["sleep", "infinity"]
