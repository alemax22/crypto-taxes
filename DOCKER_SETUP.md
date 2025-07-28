# Docker Setup Guide

This project now uses separate Docker containers for the backend (Flask) and frontend (React) applications.

## Architecture

- **Backend Container**: Flask API running on port 5000
- **Frontend Container**: React application running on port 3000
- **Shared Network**: Both containers communicate via a Docker network
- **Persistent Data**: Backend data is stored in a Docker volume

## Quick Start

### Production Mode

```bash
# Build and start both containers
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### Development Mode

```bash
# Start development containers with hot reloading
docker-compose -f docker-compose.dev.yml up --build

# Or run in background
docker-compose -f docker-compose.dev.yml up -d --build
```

## Container Details

### Backend Container (`crypto-taxes-backend`)

- **Port**: 5000
- **Base Image**: Python 3.11-slim
- **Features**:
  - Flask API server
  - Persistent data storage
  - Health checks
  - Non-root user for security

### Frontend Container (`crypto-taxes-frontend`)

- **Port**: 3000
- **Base Image**: Node.js 18-alpine
- **Features**:
  - React development server (dev mode)
  - Production build served by `serve` (prod mode)
  - Hot reloading in development
  - Health checks

## Development vs Production

### Development Mode
- **Hot Reloading**: Both frontend and backend reload automatically on code changes
- **Volume Mounts**: Source code is mounted for live editing
- **Debug Mode**: Flask runs in debug mode with auto-reload

### Production Mode
- **Optimized Builds**: Frontend is built and served statically
- **Security**: Non-root users, minimal dependencies
- **Performance**: Optimized for production workloads

## Useful Commands

### View Logs
```bash
# All containers
docker-compose logs

# Specific container
docker-compose logs backend
docker-compose logs frontend

# Follow logs
docker-compose logs -f backend
```

### Access Containers
```bash
# Access backend container
docker exec -it crypto-taxes-backend bash

# Access frontend container
docker exec -it crypto-taxes-frontend sh
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop development services
docker-compose -f docker-compose.dev.yml down
```

### Rebuild Containers
```bash
# Rebuild specific service
docker-compose build backend
docker-compose build frontend

# Rebuild all services
docker-compose build --no-cache
```

## Environment Variables

### Backend Environment Variables
- `FLASK_APP`: Flask application entry point
- `FLASK_ENV`: Environment (development/production)
- `FLASK_DEBUG`: Enable debug mode (development)
- `FLASK_RUN_HOST`: Host to bind to
- `FLASK_RUN_PORT`: Port to bind to

### Frontend Environment Variables
- `REACT_APP_API_URL`: Backend API URL
- `CHOKIDAR_USEPOLLING`: Enable file watching (development)

## Data Persistence

### Backend Data
- **Volume**: `crypto_data` (production) / `crypto_data_dev` (development)
- **Location**: `/app/persistent_data` inside container
- **Contents**: 
  - Transaction data (Parquet files)
  - OHLC price data
  - Configuration files
  - Logs

### Frontend Data
- **Volume**: Source code mounted for development
- **Build**: Static files served in production

## Networking

### Container Communication
- **Network**: `crypto-network` (production) / `crypto-network-dev` (development)
- **Backend URL**: `http://backend:5000` (internal)
- **Frontend URL**: `http://frontend:3000` (internal)

### External Access
- **Backend API**: `http://localhost:5000`
- **Frontend App**: `http://localhost:3000`

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check what's using the ports
   lsof -i :5000
   lsof -i :3000
   ```

2. **Permission Issues**
   ```bash
   # Fix volume permissions
   sudo chown -R $USER:$USER ./backend
   sudo chown -R $USER:$USER ./frontend
   ```

3. **Container Won't Start**
   ```bash
   # Check container logs
   docker-compose logs backend
   docker-compose logs frontend
   ```

4. **Build Failures**
   ```bash
   # Clean build
   docker-compose build --no-cache
   docker system prune -f
   ```

### Health Checks

Both containers have health checks configured:
- **Backend**: Checks `/api/health` endpoint
- **Frontend**: Checks if the app is responding on port 3000

### Monitoring

```bash
# Check container status
docker-compose ps

# Check resource usage
docker stats

# Check network connectivity
docker network ls
docker network inspect crypto-network
```

## File Structure

```
crypto-taxes/
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── app.py
│   ├── requirements.txt
│   └── wallets/
├── frontend/
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   ├── .dockerignore
│   ├── package.json
│   └── src/
├── docker-compose.yml
├── docker-compose.dev.yml
└── DOCKER_SETUP.md
```

## Next Steps

1. **API Configuration**: Update frontend to use the correct backend URL
2. **Environment Variables**: Set up proper environment variables for production
3. **SSL/TLS**: Add HTTPS support for production deployment
4. **Monitoring**: Add logging and monitoring solutions
5. **CI/CD**: Set up automated deployment pipelines 