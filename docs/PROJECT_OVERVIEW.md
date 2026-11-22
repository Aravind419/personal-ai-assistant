# Project Overview: Personal AI Assistant

## 1. Project Purpose & Vision

The **Personal AI Assistant** is an autonomous, production-grade AI system designed specifically for a **single personal user**. Unlike general multi-tenant chat software, this project prioritizes:
- **Persistent Personal Memory**: Lifelong knowledge extraction, semantic recall, and contextual awareness of user preferences, history, and active projects.
- **Deterministic Tool Execution**: Reliable interaction with local and cloud APIs, filesystem operations, and external services with human-in-the-loop guardrails for sensitive actions.
- **Background Proactive Automation**: Asynchronous background workers capable of executing recurring tasks, system monitoring, and automated briefings without requiring constant active chat prompting.
- **Hybrid Deployment Model**: Seamless combination of local development (Docker, Python, Node, pgvector) with modern cloud model APIs (e.g. OpenAI).

---

## 2. Core Capabilities & Goals

| Capability | Purpose & Description | Target Phase |
|---|---|---|
| **Diagnostic Foundation** | Production-ready FastAPI + React shell with health and DB latency probes | Phase 0 (VERIFIED) |
| **Conversational Agent Engine** | Streaming chat interface with LangGraph state machine and OpenAI provider abstraction | Phase 1 (Next) |
| **Activity Logging & Settings** | Structured audit trail of system events, agent thoughts, and configuration controls | Phase 1 |
| **Semantic Long-Term Memory** | Automatic memory extraction and vector search via PostgreSQL `pgvector` | Phase 2 |
| **Background Task Workers** | Asynchronous task scheduling and proactive routines powered by Redis and Celery | Phase 2 |
| **Tool & Skill Registry** | Extensible tool ecosystem with parameter validation and MCP server bridging | Phase 3 |
| **Human-in-the-Loop Approvals** | Granular approval workflow before executing destructive or high-impact actions | Phase 3 |
| **Third-Party Integrations** | OAuth and webhook connectors for calendars, email, and cloud services | Phase 4 |

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

### Database & Storage
- **Primary Database**: PostgreSQL 16
- **Vector Search Engine**: `pgvector` (Extension pre-configured in Alembic migrations)
- **ORM & Drivers**: SQLAlchemy 2.0 (AsyncIO), `asyncpg`, `psycopg`
- **Schema Migrations**: Alembic

### Infrastructure & Tooling
- **Containerization**: Docker Compose (`pgvector/pgvector:pg16`)
- **Package Management**: `uv` / `pip` for Python, `npm` for Node.js
- **Testing**: Pytest, pytest-asyncio, httpx, Playwright MCP
