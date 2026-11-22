# Project Overview: Personal AI Assistant

## 1. Project Purpose & Vision

The **Personal AI Assistant** is an autonomous, production-grade AI system designed specifically for a **single personal user**. Unlike general multi-tenant chat software, this project prioritizes:
- **Persistent Personal Memory**: Lifelong knowledge extraction, semantic recall, and contextual awareness of user preferences, history, and active projects (Phase 2).
- **Deterministic Tool Execution**: Reliable interaction with local and cloud APIs, filesystem operations, and external services with human-in-the-loop guardrails for sensitive actions (Phase 3).
- **Background Proactive Automation**: Asynchronous background workers capable of executing recurring tasks, system monitoring, and automated briefings without requiring constant active chat prompting (Phase 2/4).
- **Provider-Independent Multi-Model Intelligence**: Modular adapter-based AI layer supporting free and paid models without vendor lock-in, with strict Free-Only guardrails, fallback chains, and transparent token cost tracking.
- **Hybrid Deployment Model**: Seamless combination of local development (Docker PostgreSQL + pgvector, Python 3.13, Node 24) with external API gateways (OpenRouter active; NVIDIA NIM & local Ollama stubs prepared).

---

## 2. Core Capabilities & Goals

| Capability | Purpose & Description | Target Phase |
|---|---|---|
| **Diagnostic Foundation** | Production-ready FastAPI + React shell with health and DB latency probes | Phase 0 (VERIFIED) |
| **Conversational Agent Engine** | Streaming chat interface with persistent conversations and provider abstraction | Phase 1 (VERIFIED) |
| **Multi-Model & Cost Controls** | Central model registry, Free-Only mode, automated fallback chains, and telemetry | Phase 1 (VERIFIED) |
| **Semantic Long-Term Memory** | Automatic memory extraction and vector search via PostgreSQL `pgvector` | Phase 2 (Next - NOT_STARTED) |
| **Background Task Workers** | Asynchronous task scheduling and proactive routines powered by Redis and Celery | Phase 2 (Next - NOT_STARTED) |
| **Tool & Skill Registry Expansion** | Extensible tool ecosystem with parameter validation and MCP server bridging | Phase 3 (NOT_STARTED) |
| **Human-in-the-Loop Approvals** | Granular approval workflow before executing destructive or high-impact actions | Phase 3 (NOT_STARTED) |
| **Third-Party Integrations** | OAuth and webhook connectors for calendars, email, and cloud services | Phase 4 (NOT_STARTED) |

---

## 3. System User Model

- **Single Personal User**: The application is tailored for one owner. This eliminates unnecessary multi-tenant SaaS complexity, organizations, and team-tier logic, allowing the security perimeter, memory model, and tools to be uniquely personalized and locked down to the owner.
- **Access Boundary**: Secured at the network and local boundary with strict CORS policies, token authentication, and secret segregation.

---

## 4. Technology Stack Summary

### Frontend
- **Framework**: React 19 (Functional components, hooks)
- **Language**: TypeScript 5.9+ (Strict type safety)
- **Build Tool**: Vite 8 with Hot Module Replacement (HMR)
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite`)
- **Icons**: Lucide React

### Backend
- **Framework**: FastAPI 0.115+ (Asynchronous ASGI application)
- **Runtime**: Python 3.13
- **Data Validation & Settings**: Pydantic v2 & Pydantic Settings
- **Server**: Uvicorn
- **AI Engine**: Provider-independent adapter architecture (`BaseLLMProvider`), dynamic `ProviderRegistry`, Central Model Registry (100+ models), OpenRouter adapter, SSE streaming

### Database & Storage
- **Primary Database**: PostgreSQL 16 (Local Docker container: `pgvector/pgvector:pg16`)
- **Vector Search Engine**: `pgvector` (Extension hook configured in Alembic migrations)
- **ORM & Drivers**: SQLAlchemy 2.0 (AsyncIO, NullPool), `asyncpg`, `psycopg`
- **Schema Migrations**: Alembic

### Infrastructure & Planned Tooling
- **Containerization**: Docker Compose (`pgvector/pgvector:pg16`)
- **Background Workers**: Redis + Celery (Planned for Phase 2)
- **Package Management**: `uv` / `pip` for Python, `npm` for Node.js
- **Testing**: Pytest, pytest-asyncio, httpx, Playwright MCP
