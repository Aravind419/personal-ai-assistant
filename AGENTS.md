# Operating Rules for AI Coding Agents (AGENTS.md)

Welcome to the **Personal AI Assistant** project. This file specifies mandatory operating rules, development standards, architectural boundaries, and procedures that **all** AI coding agents (Antigravity, Cursor, Codex, Claude Code, etc.) and human developers must follow.

---

## 1. What This Project Is

The **Personal AI Assistant** is a production-grade, long-term personal agent system engineered for a **single personal user**. It provides:
- A responsive web dashboard (React 19, TypeScript, Tailwind CSS v4, Lucide Icons, Vite).
- An asynchronous high-throughput REST backend (Python 3.13, FastAPI, Pydantic v2, Uvicorn).
- A relational database with vector search capability (PostgreSQL 16, SQLAlchemy 2.x async, Alembic, pgvector).
- A provider-independent multi-model architecture supporting free and commercial models (OpenRouter adapter active, NVIDIA NIM & local Ollama stubs prepared), operational modes (Free-Only, Paid-Enabled, Manual), automated fallback chains, and token/cost telemetry.
- Future scheduled phases: semantic memory extraction (Phase 2), Redis + Celery background workers (Phase 2), tool execution expansion & human-in-the-loop approvals (Phase 3), and proactive automations & integrations (Phase 4).

---

## 2. Documentation Directory Map

Before making modifications, read the required core documentation located in [docs/](file:///d:/personal-ai-assistent/docs):
- [docs/PROJECT_OVERVIEW.md](file:///d:/personal-ai-assistent/docs/PROJECT_OVERVIEW.md) — Project purpose, user model, core capabilities, technology stack.
- [docs/ARCHITECTURE.md](file:///d:/personal-ai-assistent/docs/ARCHITECTURE.md) — Detailed architecture, component layout, data flows, multi-model engine, and design principles.
- [docs/ROADMAP.md](file:///d:/personal-ai-assistent/docs/ROADMAP.md) — Implementation phases (Phase 0 to Phase 4), dependencies, acceptance criteria.
- [docs/PROJECT_STATUS.md](file:///d:/personal-ai-assistent/docs/PROJECT_STATUS.md) — Current implementation state, verified test outputs, stopping point, next task.
- [docs/DECISIONS.md](file:///d:/personal-ai-assistent/docs/DECISIONS.md) — Architectural Decision Records (ADRs) with context and rationale.
- [docs/CHANGELOG.md](file:///d:/personal-ai-assistent/docs/CHANGELOG.md) — Chronological history of implementation milestones and modifications.
- [docs/SECURITY.md](file:///d:/personal-ai-assistent/docs/SECURITY.md) — Security rules, credentials handling, CORS, single-user guardrails, and cost protection.
- [docs/DEVELOPMENT.md](file:///d:/personal-ai-assistent/docs/DEVELOPMENT.md) — Setup instructions, run scripts, testing protocols, and troubleshooting.

---

## 3. Current Development Phase

- **Completed Phases**:
  - **Phase 0 (Engineering Foundation) — VERIFIED**
  - **Phase 1 (Basic AI Agent Implementation) — VERIFIED**
  - **Multi-Model Architecture & Cost Controls — VERIFIED**
- **Next Phase**: **Phase 2 (Semantic Memory & Background Workers) — NOT_STARTED**

> [!IMPORTANT]
> Phase 2 is NOT started. Do not jump ahead into implementing Phase 2 (pgvector semantic memory, Redis + Celery workers) or Phase 3 (Tool execution / approvals) without explicit user initiation and adhering to the planned task breakdown.

---

## 4. Technology Stack & Architectural Constraints

### Technology Stack
- **Frontend**: React 19, TypeScript 5.9+, Vite 8, Tailwind CSS v4 (`@tailwindcss/vite`), Lucide React.
- **Backend**: Python 3.13, FastAPI 0.115+, Pydantic v2 / Pydantic Settings, Uvicorn, SQLAlchemy 2.0 (Async, NullPool), Alembic.
- **AI Engine**: Provider-independent adapter architecture (`BaseLLMProvider`), dynamic `ProviderRegistry`, Central Model Registry, OpenRouter unified gateway, Server-Sent Events (SSE) streaming.
- **Database & Storage**: PostgreSQL 16 (local via Docker Compose `pgvector/pgvector:pg16`), pgvector extension enabled. *(Note: Cloud migration to Neon is deferred until future cloud deployment).*
- **Future Infrastructure (Phase 2)**: Redis and Celery planned for background task worker queues.
- **Testing**: Pytest, pytest-asyncio, httpx (backend); TypeScript `tsc -b`, Vite build (frontend).

### Strict Architectural Constraints & Guardrails
1. **Single-User Architecture**: No multi-tenant user authentication tables or organization schemas. Keep security tight around the single personal user boundary.
2. **Provider Independence**: No single commercial provider (such as OpenAI) is mandatory. The core engine communicates via normalized schemas and provider adapters. Users can use free models without paying for API tokens.
3. **Strict Free-Only Guardrails**: Under `free_only` mode, the backend strictly rejects paid models and sanitizes fallback chains to prevent accidental cloud spending.
4. **Strict Phase Boundaries & Zero-Mock Principle**: Never claim or mock an unbuilt feature. UI placeholders must explicitly state their phase status rather than generating fake simulated data.
5. **No Secret Leakage**:
   - Backend secrets (`SECRET_KEY`, database passwords, provider API keys) must NEVER be exposed in frontend bundles or prefixed with `VITE_`.
   - Never log raw database connection strings containing credentials (use the existing `sanitized_database_url` utility).
   - Provider API keys stored in PostgreSQL must be encrypted at rest with Fernet symmetric keys.
6. **Resilient Startup**: The backend must handle database unavailability gracefully (entering `degraded` mode rather than crashing), allowing diagnostic probes to run.

---

## 5. Folder Structure & Coding Conventions

```
personal-ai-assistent/
├── AGENTS.md                  # This file: operating rules & agent guidelines
├── README.md                  # Public project documentation & quickstart
├── docker-compose.yml         # Container definitions (PostgreSQL + pgvector)
├── .env.example               # Root environment template
├── docs/                      # Centralized documentation system
│   ├── PROJECT_OVERVIEW.md
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── PROJECT_STATUS.md
│   ├── DECISIONS.md
│   ├── CHANGELOG.md
│   ├── SECURITY.md
│   └── DEVELOPMENT.md
├── backend/                   # Python FastAPI service
│   ├── app/
│   │   ├── main.py            # Lifespan, CORS, router mounting
│   │   ├── api/               # Router & versioned routes (/api/v1)
│   │   ├── core/              # Config (pydantic-settings), logging, exceptions
│   │   ├── database/          # Async engine, session dependency (get_db), ping probe
│   │   ├── models/            # SQLAlchemy declarative models (TimestampMixin)
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   └── services/          # Business logic services
│   ├── alembic/               # Database migrations
│   └── tests/                 # Pytest test suite
└── frontend/                  # React + TypeScript client
    ├── src/
    │   ├── App.tsx            # Root shell & active view router
    │   ├── components/        # UI components (layout, common indicators)
    │   ├── config/            # Type-safe environment access (env.ts)
    │   ├── pages/             # Page views (DashboardOverview, PlaceholderView)
    │   ├── services/          # Typed API clients (api.ts, healthService.ts)
    │   └── types/             # TypeScript interfaces and contracts
    └── vite.config.ts
```

### Coding Conventions
- **Python / Backend**:
  - Python 3.13 typing syntax (e.g. `list[str]`, `str | None`).
  - Async-first for database and I/O endpoints (`async def`).
  - Standardized RFC-style JSON error responses via `app.core.exceptions`.
  - All database models must inherit from `Base` and `TimestampMixin` (`app.database.base`).
- **TypeScript / Frontend**:
  - Strict typing enabled; no implicit `any`.
  - Functional React components with standard React 19 hooks.
  - Utility styling via Tailwind CSS v4 classes; avoid custom inline styles.
  - API errors handled gracefully with typed error envelopes and accessible error alerts.

---

## 6. How to Run Frontend & Backend

### Database (PostgreSQL + pgvector)
```powershell
docker compose up -d postgres
```

### Backend (FastAPI)
```powershell
cd backend
# Activate virtual environment
.\.venv\Scripts\Activate.ps1
# Run migrations (if DB running)
alembic upgrade head
# Start development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive docs: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)

### Frontend (React + Vite)
```powershell
cd frontend
npm run dev
```
Client URL: [http://localhost:5173](http://localhost:5173)

---

## 7. How to Run Tests

### Backend Tests
```powershell
& "backend\.venv\Scripts\pytest" backend
```
Acceptance criteria: 100% passing tests (all 30 core tests across health, config, exceptions, security, conversations, chat stream, tools, and model registry).

### Frontend Build & Typecheck
```powershell
cd frontend
npm run build
```
Acceptance criteria: Clean `tsc -b` compilation and Vite production bundle generation with 0 errors.

---

## 8. Security Requirements

1. **Zero Secret Check-ins**: Never commit `.env`, private keys, database credentials, or API tokens to Git.
2. **CORS Restrictions**: Explicitly restrict CORS origins in `backend/app/core/config.py`. Never use wildcard `*` with credentials.
3. **Redaction**: All logging pipelines must sanitize database URLs and sensitive tokens before writing to stdout or log files.
4. Review [docs/SECURITY.md](file:///d:/personal-ai-assistent/docs/SECURITY.md) for full security requirements.

---

## 9. Documentation Update Requirements

Whenever any logical feature, task, or milestone is implemented:
1. Update [docs/PROJECT_STATUS.md](file:///d:/personal-ai-assistent/docs/PROJECT_STATUS.md) with exact progress, passing tests, and stopping record.
2. Update [docs/CHANGELOG.md](file:///d:/personal-ai-assistent/docs/CHANGELOG.md) with chronological entries.
3. Update [docs/ROADMAP.md](file:///d:/personal-ai-assistent/docs/ROADMAP.md) if phase deliverables or acceptance criteria shift.
4. Update [docs/ARCHITECTURE.md](file:///d:/personal-ai-assistent/docs/ARCHITECTURE.md) if models, services, or data flows change.
5. Update [docs/DECISIONS.md](file:///d:/personal-ai-assistent/docs/DECISIONS.md) if architectural decisions or trade-offs are made.
6. Update [docs/DEVELOPMENT.md](file:///d:/personal-ai-assistent/docs/DEVELOPMENT.md) if dependencies or run commands change.
7. Update [docs/SECURITY.md](file:///d:/personal-ai-assistent/docs/SECURITY.md) if permission models, network rules, or auth boundaries change.

Use consistent task statuses:
`NOT_STARTED` | `IN_PROGRESS` | `IMPLEMENTED` | `VERIFIED` | `BLOCKED`

*(Note: Never set status to `VERIFIED` without executing and passing the corresponding tests).*

---

## 10. How to Inspect the Project & Resume Unfinished Work

### Mandatory Session-Start Procedure
Before writing code or running implementation tools in any session:
1. Read this file ([AGENTS.md](file:///d:/personal-ai-assistent/AGENTS.md)).
2. Read [docs/PROJECT_OVERVIEW.md](file:///d:/personal-ai-assistent/docs/PROJECT_OVERVIEW.md) and [docs/ARCHITECTURE.md](file:///d:/personal-ai-assistent/docs/ARCHITECTURE.md).
3. Read [docs/ROADMAP.md](file:///d:/personal-ai-assistent/docs/ROADMAP.md) and [docs/PROJECT_STATUS.md](file:///d:/personal-ai-assistent/docs/PROJECT_STATUS.md).
4. Read recent entries in [docs/DECISIONS.md](file:///d:/personal-ai-assistent/docs/DECISIONS.md) and [docs/CHANGELOG.md](file:///d:/personal-ai-assistent/docs/CHANGELOG.md).
5. Inspect current Git changes (`git status`, `git diff`) without overwriting user work.
6. Verify the last known verified state by running tests.
7. Identify the exact next task recorded under "Next Implementation Task" in [docs/PROJECT_STATUS.md](file:///d:/personal-ai-assistent/docs/PROJECT_STATUS.md) and resume seamlessly.

---

## 11. MANDATORY DOCUMENTATION AND PROJECT CONTINUITY RULES

1. **Mandatory Pre-Task Reading**: Before every development task or phase, read `AGENTS.md` and all relevant documentation inside `docs/`, including project overview, architecture, roadmap, project status, decisions, changelog, development, and security documentation.
2. **Ground Truth Code & Schema Inspection**: Inspect the actual source code, database schema, migrations, APIs, and tests to verify the documented implementation state before making changes. Do not rely on assumptions or conversational memory.
3. **No Conversational Memory Assumptions**: Never assume previous conversation history is sufficient or available, even when using the same AI agent. Every session must be anchored in the repository files.
4. **Architectural Understanding & Preservation**: Understand the current architecture, completed phases, and provider abstraction. Reuse existing implementations instead of rebuilding them. Do not introduce mandatory paid API dependencies or assume all providers share identical APIs.
5. **No Fake Functionality**: Never assume an undocumented feature exists, and never introduce mock or simulated behavior presented as a completed feature. Keep placeholders honest.
6. **Continuous Status & History Logging**: Maintain `PROJECT_STATUS.md` and `CHANGELOG.md` after every meaningful development task.
7. **Proactive Documentation Synchronization**: Update other relevant documentation (`ARCHITECTURE.md`, `ROADMAP.md`, `DECISIONS.md`, `SECURITY.md`, `DEVELOPMENT.md`) whenever architecture, dependencies, APIs, database schemas, security, or workflows change.
8. **Mandatory Stopping-Point Record**: Before ending a session, record completed work, verified work, incomplete work, bugs, blockers, test results, and the exact next task in `PROJECT_STATUS.md`.
9. **Complete Agent Interchangeability**: Make the project understandable and resumable by a completely new AI agent without access to previous conversation history. Future phases must adhere to the existing roadmap unless the user explicitly approves a modification.
10. **Strict Verification Integrity**: Never mark something `VERIFIED` without actual successful verification (running tests and builds).
11. **Preserve Decision & Evolution History**: Preserve historical documentation and existing project decisions; never erase prior context or accepted ADRs without a formal decision update.
12. **Secret Hygiene**: Never expose API keys, credentials, `.env` values, or other secrets in documentation, logs, or Git commits.
13. **Repository as Source of Truth**: Treat the repository documentation and actual implementation as the long-term, authoritative source of truth. Never overwrite documentation without inspecting and preserving its contents.
