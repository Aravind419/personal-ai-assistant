# Architectural Decision Records (ADRs)

This document records key technical and architectural decisions, the context in which they were made, alternatives considered, and the resulting rationale.

---

## ADR-001: Single-User Architecture vs. Multi-Tenant SaaS
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  The system is being designed as a personal AI assistant. Multi-tenant designs require extensive tenant isolation, RBAC schemas, complex database row-level security (RLS), and organization billing layers.
- **Decision**:
  Implement the application explicitly for a single personal user.
- **Consequences**:
  - Eliminates multi-tenant schema overhead and complexity.
  - Personal memory, local filesystem access, and tool executions are securely bounded to the owner's machine.
  - Security perimeter focuses on local network boundaries, strict CORS, and local secret management.

---

## ADR-002: Framework Stack (FastAPI + React 19 + TypeScript + Vite)
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  We needed a modern, high-throughput asynchronous backend capable of streaming LLM outputs and interfacing with AI ecosystems (Python), paired with a responsive, maintainable frontend interface.
- **Decision**:
  - Backend: Python 3.13 with FastAPI and Uvicorn.
  - Frontend: React 19 with TypeScript 5.9+ and Vite 8 bundler.
  - Styling: Tailwind CSS v4 (`@tailwindcss/vite`).
- **Consequences**:
  - Python provides immediate native compatibility with AI frameworks (LangGraph, OpenAI, Celery).
  - FastAPI provides native async support, Pydantic v2 validation, and OpenAPI documentation out-of-the-box.
  - React + Vite provides instant HMR, lightweight build artifacts, and responsive cross-device usability.

---

## ADR-003: Single Database Architecture with PostgreSQL & pgvector
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Personal agents require relational persistence (users, sessions, task logs, audit trails) and vector search for semantic long-term memory. Dual-database setups (e.g., PostgreSQL for relational + Pinecone/Qdrant for vectors) introduce synchronization lag, dual backup maintenance, and higher operational cost.
- **Decision**:
  Use a unified PostgreSQL 16 database with the `pgvector` extension enabled via Alembic migrations.
- **Consequences**:
  - ACID transactions across relational metadata and vector embeddings in a single database.
  - Simplifies local deployment via a single Docker service (`pgvector/pgvector:pg16`).
  - Native SQLAlchemy integration for both tabular and vector queries.

---

## ADR-004: Resilient Backend Startup & Degraded State Handling
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  If a developer or user starts the backend before starting the PostgreSQL Docker container, crashing the application leaves no actionable diagnostics or responsive health probes.
- **Decision**:
  Implement non-fatal startup health checks in `app/main.py`. If the database cannot be reached during initialization, log a sanitized warning and transition the application state into `degraded`.
- **Consequences**:
  - The API stays alive and returns informative JSON via `/api/v1/health` and `/api/v1/health/db`.
  - Frontend dashboard can cleanly notify the user that PostgreSQL is offline and provide recovery commands.

---

## ADR-005: Strict Credential Sanitization in Logging
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Database connection strings and environment variables often contain sensitive passwords, tokens, or API keys that risk leaking into terminal output or log aggregators.
- **Decision**:
  Build a dedicated sanitization utility (`sanitized_database_url` in `app/core/config.py` and `RedactingFormatter` in `app/core/logging.py`) that uses regular expressions to mask passwords (`user:***@host`).
- **Consequences**:
  - Guarantees zero accidental leakage of credentials in logs.
  - Standardized practice across all logging output.

---

## ADR-006: Phase-Gated Functional Boundaries & Zero-Mock Principle
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  AI coding agents frequently generate superficial mock data or fake interactive buttons for features that have not yet been built (e.g. fake chat responses, mock task triggers).
- **Decision**:
  Strict zero-mock policy. Unbuilt features must use informational placeholders (`PlaceholderView`) clearly stating the target phase and prerequisites.
- **Consequences**:
  - Prevents confusing fake interactions.
  - Maintains total engineering integrity across all phases.
