# Development Guide & Troubleshooting

## 1. Prerequisites

Ensure the following tools are installed on your host system:
- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: 3.11+ (Python 3.13 recommended)
- **Node.js**: 20.x or 24.x (Active LTS)
- **Package Managers**: `uv` (recommended) or `pip`, `npm`
- **Docker**: Docker Desktop (for PostgreSQL container)
- **Git**: 2.40+

---

## 2. Initial Setup

### Step 1: Environment Variables
Copy all `.env.example` templates to `.env`:

```powershell
# In project root
Copy-Item .env.example .env

# In backend directory
Copy-Item backend\.env.example backend\.env

# In frontend directory
Copy-Item frontend\.env.example frontend\.env
```

---

### Step 2: Database Initialization (Docker)

Start the PostgreSQL 16 container with `pgvector`:

```powershell
# Start container in detached mode
docker compose up -d postgres

# Check status
docker compose ps
```

To stop the container:
```powershell
docker compose down
```

To wipe database data volume:
```powershell
docker compose down -v
```

---

### Step 3: Backend Setup (FastAPI)

1. Navigate to `backend` and create a virtual environment:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Run database migrations (ensure Docker container is up):
   ```powershell
   alembic upgrade head
   ```

3. Run the automated test suite:
   ```powershell
   pytest
   ```

4. Start the backend development server:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

- Interactive OpenAPI Swagger Docs: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- Alternative Redoc: [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)
- Health Check: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

### Step 4: Frontend Setup (React + Vite)

1. Navigate to `frontend` and install dependencies:
   ```powershell
   cd frontend
   npm install
   ```

2. Verify TypeScript types and production build:
   ```powershell
   npm run build
   ```

3. Start the development server:
   ```powershell
   npm run dev
   ```

Open browser at [http://localhost:5173](http://localhost:5173).

---

## 3. Development Workflow & Testing Commands

| Purpose | Directory | Command |
|---|---|---|
| **Backend Unit & Integration Tests** | `backend` | `pytest` |
| **Backend Lint / Formatting Check** | `backend` | `ruff check .` (or `flake8`) |
| **Run Migrations** | `backend` | `alembic upgrade head` |
| **Generate Migration** | `backend` | `alembic revision --autogenerate -m "description"` |
| **Frontend Production Build** | `frontend` | `npm run build` |
| **Frontend Type Checking** | `frontend` | `npx tsc -b` |
| **Frontend Development Server** | `frontend` | `npm run dev` |

---

## 4. Troubleshooting Guide

### Issue 1: Database Connection Refused / Degraded Health
- **Symptom**: `/api/v1/health` reports status `degraded` and database ping returns `connected: false`.
- **Cause**: The PostgreSQL Docker container is not running or the port `5432` is occupied.
- **Solution**:
  1. Check Docker container: `docker compose ps`.
  2. If exited or stopped, restart: `docker compose up -d postgres`.
  3. Verify port mapping: ensure no local Postgres service is conflicting on port 5432.

### Issue 2: Alembic Migration Fails on Extension Vector
- **Symptom**: `alembic upgrade head` fails with `permission denied to create extension "vector"` or `extension "vector" is not available`.
- **Cause**: Standard PostgreSQL image used instead of `pgvector/pgvector:pg16`.
- **Solution**: Ensure `docker-compose.yml` specifies `image: pgvector/pgvector:pg16`.

### Issue 3: CORS Blocking Requests from Frontend
- **Symptom**: Browser console logs `Cross-Origin Request Blocked`.
- **Cause**: Frontend is running on a different port than `http://localhost:5173`.
- **Solution**: Add the origin to `CORS_ORIGINS` in `backend/.env` (comma-separated).
