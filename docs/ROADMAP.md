# Development Roadmap: Personal AI Assistant

## 1. Roadmap Overview & Implementation Phases

The project follows a rigorous phased engineering methodology. Each phase contains clear deliverables, strict dependencies, and non-negotiable acceptance criteria.

```
+-----------------------------------------------------------------------------------------+
| Phase 0: Engineering Foundation (VERIFIED)                                              |
| - FastAPI backend + React 19/TS shell + PostgreSQL 16/pgvector + Docker + Health Probes |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| Phase 1: Basic AI Agent Implementation (VERIFIED)                                       |
| - Provider-independent LLM architecture + OpenRouter adapter + Real-time SSE streaming  |
| - PostgreSQL conversation/message persistence + React Chat & Provider Settings UI       |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| Phase 2: Semantic Memory & Background Workers (NOT_STARTED)                             |
| - pgvector schema + memory extraction + Redis & Celery task worker + Tasks dashboard    |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| Phase 3: Tool Execution & Human-in-the-Loop Approvals (NOT_STARTED)                     |
| - Dynamic tool registry + MCP bridge + Approval workflow engine + Skills UI             |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| Phase 4: Proactive Automations & External Integrations (NOT_STARTED)                    |
| - OAuth connectors (Google/GitHub) + Cron/event automations + System Audit              |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Detailed Phase Specifications

### Phase 0: Engineering Foundation
- **Status**: `VERIFIED`
- **Dependencies**: None
- **Key Deliverables**:
  - Modular FastAPI backend application with lifespan management, CORS, structured logging, centralized exceptions.
  - Asynchronous database engine (SQLAlchemy 2.x, Alembic, `asyncpg`/`psycopg`) with connection ping probe.
  - Docker Compose configuration for PostgreSQL 16 with pre-configured pgvector hook.
  - React 19 + TypeScript + Vite responsive dashboard shell with 11-module navigation.
  - Diagnostic Overview dashboard showing live backend health, DB connection status, latency, and system metadata.
  - Automated test suite (9 passing Pytest tests) and production Vite build with 0 TypeScript errors.

---

### Phase 1: Basic AI Agent Implementation & Multi-Model Architecture
- **Status**: `VERIFIED`
- **Dependencies**: Phase 0 (VERIFIED)
- **Key Deliverables**:
  - **Provider-Independent Architecture**: Abstract `BaseLLMProvider` interface and dynamic `ProviderRegistry` (`backend/app/providers/`).
  - **OpenRouter Adapter**: Complete, genuine adapter supporting Server-Sent Events (SSE) streaming, credential verification, model listing, and error normalization.
  - **Future Provider Stubs**: Prepared adapter structures for NVIDIA NIM and local Ollama (`app/providers/adapters/nvidia.py`, `app/providers/adapters/ollama.py`).
  - **Encrypted Credential Storage**: Symmetric encryption (Fernet) for persisted API keys with derived key from `SECRET_KEY`.
  - **Central Model Registry**: Catalog of 100+ models with context windows, capabilities, and pricing classification (`free` vs `paid`).
  - **Operational Policy Engine**: Strict `free_only` mode (blocks paid models and purges them from fallbacks), `paid_enabled` mode with per-request cost caps, and `manual` mode.
  - **Multi-Model Fallback Chains**: Seamless failover to fallback models upon 429 rate limits or provider errors with real-time client SSE notices.
  - **Token & Cost Telemetry**: Model execution metrics recorded per request (prompt tokens, completion tokens, latency, cost estimation in USD).
  - **Database Persistence**: Tables `provider_configurations`, `conversations`, `messages`, `ai_model_policies`, and `model_execution_metrics` managed through Alembic migrations (`002` and `003`).
  - **Conversation Management**: Full thread CRUD endpoints under `/api/v1/conversations`.
  - **Real-Time Streaming Endpoint**: `/api/v1/conversations/{id}/messages` yielding SSE token deltas and persisting user/assistant turns in PostgreSQL.
  - **Interactive Chat Interface**: React Chat page with conversation history sidebar, thread creation, model switching (grouped by Free vs Paid), mode pill indicator, Markdown formatting, code copy, and auto-scroll.
  - **Provider Settings Interface**: Settings page for entering credentials, selecting default models, live connection testing, operational mode selection, fallback chain priority reordering, and usage telemetry dashboard.
  - **Tool-Calling Foundation**: Backend tool registry and parameter validation with safe baseline tools (`SystemClockTool`, `CalculatorTool`).
- **Acceptance Criteria**:
  - [x] Provider-independent architecture decoupled from any single vendor (OpenAI not mandatory).
  - [x] OpenRouter adapter completely implemented and functional with free and paid models.
  - [x] Strict Free-Only guardrails prevent accidental commercial token expenditure.
  - [x] Fallback chains seamlessly handle rate limits and notify client in real-time.
  - [x] Real-time token streaming via Server-Sent Events (SSE) verified.
  - [x] Conversations and message history persist across server restarts in PostgreSQL.
  - [x] API keys encrypted at rest and never leaked in API responses.
  - [x] Automated tests passing (all 30 pytest tests pass).
  - [x] Browser workflows verified via Playwright MCP.

---

### Phase 2: Semantic Memory & Background Workers
- **Status**: `NOT_STARTED`
- **Dependencies**: Phase 1 (VERIFIED)
- **Key Deliverables**:
  - **Semantic Vector Store**: Database tables for storing vector embeddings using PostgreSQL `pgvector`.
  - **Memory Extraction Pipeline**: Automatic extraction of user facts, preferences, and entities from conversations.
  - **Redis & Celery Worker**: Asynchronous task queue running in a dedicated Docker service.
  - **Tasks View**: Interactive task dashboard displaying background task states, schedules, and historical outputs.
  - **Memory Exploration View**: Searchable UI for inspecting and managing stored personal facts and embeddings.

---

### Phase 3: Tool Execution & Human-in-the-Loop Approvals
- **Status**: `NOT_STARTED`
- **Dependencies**: Phase 2 (NOT_STARTED)
- **Key Deliverables**:
  - **Tool Registry Expansion**: Broaden registry for executing local tools with strict argument validation.
  - **MCP Bridge**: Model Context Protocol client for connecting external MCP servers.
  - **Human-in-the-Loop Approval Engine**: Gatekeeper system requiring explicit user confirmation before executing potentially destructive or sensitive actions.
