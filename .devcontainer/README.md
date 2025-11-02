# Dev Container Setup

This directory contains the configuration for VS Code Dev Containers, allowing you to develop in a consistent, containerized environment.

## What's Included

- **Backend**: Python 3.11 with FastAPI, all dependencies installed
- **Frontend**: Node.js 18 with React
- **PostgreSQL**: Database service running on port 5432

## Getting Started

1. Open the project in VS Code
2. When prompted, click "Reopen in Container" (or use Command Palette: `Dev Containers: Reopen in Container`)
3. Wait for the containers to build and start

## Services

### Backend (Port 5000)
- The main dev container connects to the backend service
- To start the FastAPI server:
  ```bash
  cd /workspace/backend
  python -m uvicorn app:app --host 0.0.0.0 --port 5000 --reload
  ```

### Frontend (Port 3000)
- Runs in a separate container
- To install dependencies (first time only):
  ```bash
  docker exec -it crypto-taxes-frontend-dev npm install
  ```
- To start the development server:
  ```bash
  docker exec -it crypto-taxes-frontend-dev npm start
  ```
- Or access the container's terminal via VS Code's Docker extension

### PostgreSQL (Port 5432)
- Connection details:
  - Host: `postgres` (from within containers) or `localhost` (from host)
  - Database: `cryptotaxes`
  - User: `cryptotaxes`
  - Password: `cryptotaxes`

## Development Tools

The dev container includes:
- Python extensions (Pylance, Black formatter, isort)
- ESLint and Prettier for JavaScript
- Docker extension
- SQL Tools for PostgreSQL

## Running Tests

```bash
cd /workspace/backend
pytest
```

## Notes

- The workspace is mounted at `/workspace`
- All three services (backend, frontend, postgres) start automatically
- Ports are automatically forwarded to your host machine
- Changes to code are reflected immediately due to volume mounts

