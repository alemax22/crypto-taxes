# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A crypto portfolio tracker and tax calculator targeting Italian 2025 tax regulations (26% tax rate, €2000 exemption, FIFO method). Full-stack app with a FastAPI backend, React frontend, and PostgreSQL database, all orchestrated via Docker Compose.

## Running the Project

**Recommended: Docker Compose**
```bash
docker-compose up --build -d
# Backend: http://localhost:5000
# Frontend: http://localhost:3000
```

**Manual:**
```bash
# Backend (from repo root)
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 5000

# Frontend
cd frontend && npm install && npm start
```

**Reset everything:**
```bash
docker-compose down -v && docker-compose up --build -d
```

## Backend Commands

```bash
# Run tests
pytest

# Run specific test file
pytest test/test_wallet_kraken.py

# Run with coverage
pytest --cov=wallets --cov-report=term-missing

# Run by marker
pytest -m unit
pytest -m integration
```

## Frontend Commands

```bash
cd frontend
npm start       # dev server on port 3000
npm test        # run tests
npm run build   # production build
```

## Architecture
The backend is developed according to a domanin driven design.

### Backend (FastAPI, Python 3.11+)

Entry point: `app.py` — registers CORS, mounts routes.

The domain logic lives in `wallets/`:
- **`portfolio.py`** — `Portfolio` aggregate managing a collection of wallets
- **`wallet_kraken.py`** — Kraken-specific `Wallet` implementation via `krakenex`/`pykrakenapi`
- **`repository.py`** — Repository interfaces + `PostgresWalletRepository` / `PostgresPortfolioRepository` (SQLAlchemy 2.0)
- **`db.py`** — SQLAlchemy engine/session setup

`config.py` holds tax configuration constants (rates, thresholds, FIFO settings).

Fernet symmetric encryption protects API credentials at rest; the encryption key is stored in `/app/persistent_data/config/`.

### Frontend (React 18, React Router v6)

Entry: `frontend/src/App.js`

Pages: `Dashboard`, `Wallets`, `WalletDetails` — all in `src/pages/`.
Components: `PortfolioChart`, `TransactionTable`, `WalletCard`, `AddWalletModal`, etc. — in `src/components/`.

State management is local; data fetching is done directly with Axios. The dev server proxies `/` to `http://backend:5000`.

### Database (PostgreSQL 16)

Two main tables: `portfolios` and `wallets` (with encrypted `api_key`/`api_secret` columns). Parquet files under `/app/persistent_data/data/` store OHLC and transaction history.

### Service Communication

All three containers share the `crypto-network` bridge. The frontend container reaches the backend via the `backend` hostname. The backend reaches PostgreSQL via the `db` hostname.

## Testing Strategy

Tests live in `test/`. The project uses pytest markers:
- `unit` — isolated, mocked (preferred for fast feedback)
- `integration` — hits real database or filesystem
- `slow`, `api` — network-dependent

Mock philosophy: API calls, file I/O, and cryptography are mocked in unit tests to avoid side effects. See `test/TESTING.md` for full mocking strategy.
