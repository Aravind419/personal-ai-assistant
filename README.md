# Personal AI Agent — Phase 0 Foundation

A production-grade engineering foundation for an autonomous personal AI assistant. Designed for a single personal user with persistent memory, tool execution, background automation, and hybrid cloud/local capabilities.

> **Phase 0 Status**: The foundational engineering layers (FastAPI backend, React+TypeScript dashboard shell, PostgreSQL connectivity, Docker Compose, and diagnostic probes) are fully implemented and verified. AI orchestration and background task execution are scheduled for subsequent phases.

---

## 1. Architectural Stack

- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons.
- **Backend**: Python 3.13, FastAPI, Uvicorn, Pydantic v2.
- **Database & ORM**: PostgreSQL 16, SQLAlchemy 2.x (Async), Alembic, `asyncpg` / `psycopg`.
- **Vector Search (Prepared)**: `pgvector` container & schema hooks.
- **Future Orchestration**: LangGraph (Phase 1+).
- **Future Background Tasks**: Redis + Celery (Phase 2+).
- **Security Boundary**: Single-user design, strict secret hygiene, restricted CORS.

---

## 2. Directory Layout

```
personal-ai-assistent/
├── .env.example                 # Root environment template
├── .gitignore                   # Ignore rules for Python, Node, DB, secrets
├── docker-compose.yml           # PostgreSQL + pgvector service definition
├── README.md                    # Quickstart & setup documentation
├── docs/
│   ├── architecture.md          # Detailed architecture specification
│   └── phase-0.md               # Phase 0 deliverables & verification report
├── backend/
│   ├── .env.example             # Backend environment template
│   ├── pyproject.toml           # Backend packaging & test configuration
│   ├── requirements.txt         # Pinned backend dependencies
│   ├── alembic.ini              # Alembic migration configuration
│   ├── alembic/                 # Database migration scripts
│   ├── app/
│   │   ├── main.py              # FastAPI app instance, CORS & lifespan
│   │   ├── api/                 # Versioned routes (/api/v1/health, /info)
│   │   ├── core/                # Settings, logging, centralized exceptions
│   │   ├── database/            # Async engine, session dependency, DB probe
│   │   ├── models/              # SQLAlchemy declarative models
│   │   ├── schemas/             # Pydantic validation & response schemas
│   │   └── services/            # Health & diagnostic services
│   └── tests/                   # Pytest test suite (100% pass)
└── frontend/
    ├── .env.example             # Frontend environment template
    ├── package.json             # Node dependencies and scripts
    ├── tsconfig.json            # TypeScript configuration
    ├── vite.config.ts           # Vite + Tailwind CSS configuration
    └── src/
        ├── App.tsx              # Root component & navigation state
        ├── components/          # Shell, Sidebar, Header, Status badges
        ├── pages/               # DashboardOverview, PlaceholderView
        ├── services/            # Typed API client & health service
        └── types/               # TypeScript interfaces
```

---

## 3. Getting Started

### Prerequisites

- **Python**: 3.11+ (Python 3.13 recommended)
- **Node.js**: 20.x or 24.x
- **Package Managers**: `uv` or `pip`, `npm`
- **Docker** (Optional for local PostgreSQL container): Docker Desktop or Docker Engine

---

### Step 1: Environment Setup

Clone the repository and copy the environment configuration templates:

```bash
# In the repository root
cp .env.example .env

# Backend configuration
cp backend/.env.example backend/.env

# Frontend configuration
cp frontend/.env.example frontend/.env
```

---

### Step 2: Database Setup

#### Option A: Using Docker Compose (Recommended)

Start the PostgreSQL service with pre-installed `pgvector`:

```bash
docker compose up -d postgres
```

To stop the database:
```bash
docker compose down
```

To reset the database volume:
```bash
docker compose down -v
```

#### Option B: Using Existing PostgreSQL Instance

If you are running PostgreSQL natively on your machine, configure `DATABASE_URL` in `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/personal_ai_db
```

#### Running Database Migrations

Apply Alembic migrations to create the initial foundation schema:

```bash
cd backend
.venv\Scripts\alembic upgrade head
```

*(Note: If PostgreSQL is not currently running, the backend will safely start in `degraded` mode and report database status gracefully.)*

---

### Step 3: Backend Setup & Startup

1. Create a Python virtual environment and install dependencies:

```bash
cd backend

# Using uv (fastest)
uv venv .venv
uv pip install -r requirements.txt

# Or using standard python
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

2. Run the backend tests to verify configuration:

```bash
.venv\Scripts\pytest
```

3. Start the FastAPI development server:

```bash
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive Swagger Docs**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **Alternative Redoc**: [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)
- **Health Diagnostic**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

### Step 4: Frontend Setup & Startup

1. Install frontend dependencies:

```bash
cd frontend
npm install
```

2. Run production build test:

```bash
npm run build
```

3. Start the Vite development server:

```bash
npm run dev
```

Open your browser at **[http://localhost:5173](http://localhost:5173)**.

---

## 4. Testing & Verification

### Test Backend API

```bash
cd backend
.venv\Scripts\pytest
```

Expected output:
```
backend\tests\test_config.py ...
backend\tests\test_exceptions.py ..
backend\tests\test_health.py ....
============================== 9 passed ==============================
```

### Direct Health Check via HTTP

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Sample JSON response:
```json
{
  "status": "healthy",
  "app_name": "Personal AI Assistant",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-11-22T04:00:00.000000Z",
  "database": {
    "connected": true,
    "latency_ms": 1.45,
    "error": null
  }
}
```

---

## 5. Scope Restrictions & Guardrails

Per project instructions, Phase 0 does **not** include:
- Artificial intelligence or LLM chat endpoints.
- Agentic reasoning loops (LangGraph).
- Memory extraction or vector embedding storage.
- Background worker processes (Celery/Redis).
- OAuth or external application credentials.

The 11 UI navigation placeholders (Chat, Tasks, Memory, Skills, Tools, Integrations, Automations, Approvals, Activity Logs, Settings) present clear phase roadmaps without fake mocked actions.

---

## 6. Next Steps

- **Phase 1**: OpenAI provider abstraction, LangGraph conversational loops, Chat UI view, and Activity Logs.
- **Phase 2**: Persistent memory extraction with pgvector, Celery task worker, and Tasks management.
- **Phase 3**: Dynamic tool registry, MCP server bridge, and Approval workflow engine.
- **Phase 4**: Third-party OAuth integrations and proactive background automations.
