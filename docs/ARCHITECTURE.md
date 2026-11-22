# System Architecture: Personal AI Assistant

## 1. High-Level Architecture Diagram

```
                              +------------------------------------------+
                              |         React + TypeScript Frontend       |
                              |   (Vite, Tailwind CSS, Component Shell)  |
                              +--------------------+---------------------+
                                                   | HTTP / REST (CORS)
                                                   v
                              +------------------------------------------+
                              |          FastAPI Backend Engine          |
                              | (Modular API, Core Config, Exception Lyr)|
                              +--------------------+---------------------+
                                                   | Async SQLAlchemy (asyncpg)
                                                   v
                              +------------------------------------------+
                              |           PostgreSQL 16 Database         |
                              |  (Alembic Migrations, pgvector Prepared) |
                              +--------------------+---------------------+
                                                   |
                        +--------------------------+--------------------------+
                        | (Phase 1)                                           | (Phase 2)
                        v                                                     v
           +-------------------------+                           +-------------------------+
           |  LangGraph Agentic Loop |                           |  Redis & Celery Workers |
           |  (OpenAI Provider Layer)|                           | (Proactive Background)  |
           +-------------------------+                           +-------------------------+
```

---

## 2. Core Architectural Decisions

| Layer | Decision | Rationale & Architectural Purpose |
|---|---|---|
| **Application Type** | Single-user personal agent | Eliminates multi-tenant SaaS overhead; simplifies security boundary to personal ownership. |
| **Interface** | Responsive Web App | Accessible across desktop, tablet, and mobile browsers without native platform limitations. |
| **Frontend** | React 19 + TypeScript + Vite | Type-safe, modular, performant developer ergonomics with instant HMR and lean builds. |
| **Styling** | Tailwind CSS v4 | Utility-first, predictable styling with standardized design tokens and zero runtime overhead. |
| **Backend** | Python 3.13 + FastAPI | High-throughput asynchronous REST API with automatic OpenAPI documentation and Pydantic validation. |
| **Database** | PostgreSQL 16 | Relational backbone with ACID transactions, JSONB extensibility, and native vector search capabilities. |
| **Vector Engine** | pgvector (Prepared) | Single-database storage eliminating dual-database synchronization issues between vectors and relational records. |
| **Orchestration** | LangGraph (Phase 1) | State-machine graph orchestration providing cyclical reasoning, memory checkpoints, and deterministic branching. |
| **AI Provider** | OpenAI API via Provider Abstraction | Isolates the agent core from specific LLM vendors; enables swap-in of local models or alternative providers. |
| **Execution** | Redis + Celery (Phase 2) | Reliable background task queue for long-running workflows, automated periodic audits, and proactive triggers. |
| **Security & Autonomy** | Guardrailed Autonomous Actions | Read-only and non-destructive tasks execute automatically; sensitive actions require human approval. |

---

## 3. Directory Layout & Module Organization

```
personal-ai-assistent/
├── AGENTS.md                  # Instructions and operating rules for AI coding agents
├── README.md                  # Project overview & quickstart guide
├── docker-compose.yml         # PostgreSQL + pgvector container configuration
├── .env.example               # Root environment variables reference
├── docs/                      # Centralized documentation system
│   ├── PROJECT_OVERVIEW.md    # Purpose, user model, tech stack
│   ├── ARCHITECTURE.md        # System architecture and technical design (this file)
│   ├── ROADMAP.md             # Implementation phases & acceptance criteria
│   ├── PROJECT_STATUS.md      # Current implementation state & continuation record
│   ├── DECISIONS.md           # Architectural decision records (ADRs)
│   ├── CHANGELOG.md           # Chronological modification history
│   ├── SECURITY.md            # Security rules, secrets handling, permissions
│   └── DEVELOPMENT.md         # Setup, run commands, testing, troubleshooting
├── backend/                   # Python FastAPI service
│   ├── .env.example           # Backend-specific environment template
│   ├── pyproject.toml         # Modern Python packaging configuration (uv/pip)
│   ├── requirements.txt       # Pinned production and test dependencies
│   ├── alembic.ini            # Database migration configuration
│   ├── alembic/
│   │   ├── env.py             # Async Alembic execution environment
│   │   ├── script.py.mako     # Migration template script
│   │   └── versions/
│   │       └── 001_initial_foundation.py  # Initial table and pgvector extension hook
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # Application entrypoint, lifespan, CORS, and routers
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py      # Centralized /api/v1 router
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── health.py  # Health diagnostics and DB ping endpoints
│   │   │       └── info.py    # Architecture metadata and phase capability state
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py      # Pydantic BaseSettings environment validation
│   │   │   ├── logging.py     # Structured logging with secret redaction
│   │   │   └── exceptions.py  # Centralized RFC-style error handlers
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── base.py        # SQLAlchemy DeclarativeBase and TimestampMixin
│   │   │   ├── connection.py  # Async engine initialization and live ping probe
│   │   │   └── session.py     # AsyncSession dependency injection
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── system.py      # SystemMetadata foundation table
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── common.py      # Generic API responses and error envelopes
│   │   │   └── health.py      # Pydantic schemas for health & diagnostics
│   │   └── services/
│   │       ├── __init__.py
│   │       └── health_service.py # Health check business logic
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py        # Asynchronous test client fixtures
│       ├── test_config.py     # Environment parsing & sanitization tests
│       ├── test_exceptions.py # Centralized error handler tests
│       └── test_health.py     # API endpoints & DB probe tests
└── frontend/                  # React 19 + TypeScript + Vite frontend
    ├── .env.example           # Frontend environment template
    ├── package.json           # Node dependencies and scripts
    ├── tsconfig.json          # Strict TypeScript configuration
    ├── vite.config.ts         # Vite + Tailwind CSS configuration
    ├── index.html             # Entry HTML shell
    └── src/
        ├── index.css          # Tailwind CSS root rules
        ├── main.tsx           # React root mount
        ├── App.tsx            # Root application router and shell container
        ├── config/
        │   └── env.ts         # Type-safe environment variable access
        ├── types/
        │   ├── api.ts         # API contract TypeScript interfaces
        │   └── navigation.ts  # Navigation configuration interfaces
        ├── services/
        │   ├── api.ts         # Fetch API wrapper with timeout & error handling
        │   └── healthService.ts # Health & diagnostics client service
        ├── components/
        │   ├── common/
        │   │   ├── StatusBadge.tsx     # Color-coded pulse indicators
        │   │   ├── LoadingState.tsx    # Animated loading indicators
        │   │   ├── ErrorState.tsx      # Diagnostic failure alerts with retry
        │   │   ├── EmptyState.tsx      # Reusable empty content container
        │   │   └── PlaceholderView.tsx # Informative phase-gated view
        │   └── layout/
        │       ├── Header.tsx          # Status indicators and refresh trigger
        │       ├── Sidebar.tsx         # Responsive 11-item navigation bar
        │       └── AppShell.tsx        # Responsive dashboard frame
        └── pages/
            └── DashboardOverview.tsx   # Foundation diagnostic dashboard
```

---

## 4. Security Principles

1. **Strict Credential Sanitization**:
   - Secrets (`SECRET_KEY`, database passwords) are never logged. The backend's `sanitized_database_url` utility redacts user:password credentials before logging connection targets.
2. **Environment Variable Isolation**:
   - Frontend and backend configurations are strictly isolated. No backend secret or private token is prefixed with `VITE_` or leaked to client bundles.
3. **Restricted CORS Policy**:
   - Cross-Origin Resource Sharing is restricted explicitly to configured development and production hosts (`CORS_ORIGINS`).
4. **Resilient Startup & Degraded State Handling**:
   - The backend validates its configuration upon startup. If the database is initially unavailable, the server logs a warning and transitions to a graceful `degraded` state without crashing, enabling diagnostic endpoints to remain responsive.
