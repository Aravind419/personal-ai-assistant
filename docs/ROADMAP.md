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
| Phase 2: Semantic Memory & Background Workers (VERIFIED)                                |
| - pgvector schema + memory extraction + Redis & Celery task worker + Tasks dashboard    |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| Formatting & Conversational Intelligence Harness (VERIFIED)                             |
| - GFM tables + Voice STT/TTS + ContextBuilder + Anti-robotic rules + Personality engine |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| Phase 3: Tool Execution & Human-in-the-Loop Approvals (VERIFIED)                        |
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
- **Status**: `VERIFIED`
- **Dependencies**: Phase 1 (VERIFIED)
- **Key Deliverables**:
  - **Semantic Vector Store**: `memories` table with 384-dimensional pgvector `Vector` column, HNSW cosine distance index, and Alembic migration `004_semantic_memory_and_tasks.py`.
  - **Provider-Independent Embedding Layer**: `BaseEmbeddingProvider` abstraction with deterministic `LocalSemanticEmbeddingProvider` (zero downloads, fast CPU inference) and OpenRouter cloud adapter.
  - **Memory Extraction & Conflict Engine**: Automatic extraction of durable facts from user/assistant messages with regex secret filtering, deduplication (similarity >= 0.85), and historical superseding.
  - **Isolated Semantic Context Retrieval**: Top-k vector retrieval with multi-factor scoring (`0.6*similarity + 0.25*importance + 0.15*confidence`) injected into system prompts as `<retrieved_context>`.
  - **Redis & Celery Worker Infrastructure**: Dockerized Redis container (`redis:7-alpine`), Celery application with execution timeouts, retries, and local async fallback.
  - **Persistent Task Management API**: `background_tasks` table and REST endpoints under `/api/v1/tasks` for listing, filtering, cancellation, and retrying.
  - **Interactive Frontend Dashboards**: `MemoryView.tsx` with search, category filtering, stats, Add/Edit modal, and `TasksView.tsx` with live 4s auto-refresh polling and action controls.
- **Acceptance Criteria**:
  - [x] pgvector memory storage verified with native HNSW cosine distance queries.
  - [x] Embedding generation works offline through provider abstraction without requiring paid keys.
  - [x] Automatic memory extraction runs asynchronously after chat responses without delaying token streaming.
  - [x] Duplicate detection, conflict resolution, and fact superseding verified.
  - [x] Semantic retrieval successfully injects relevant memories into future conversation prompts.
  - [x] Memory CRUD operates through real backend REST endpoints.
  - [x] Redis and Celery worker infrastructure operational with graceful offline fallback.
  - [x] Background task lifecycle, retries, and cancellation fully functional.
  - [x] Memory Explorer and Tasks Dashboard display real PostgreSQL data.
  - [x] All 71 backend tests pass; clean frontend production build with 0 errors.
  - [x] End-to-end browser workflows verified via Playwright MCP.

---

### Pre-Phase 3 Upgrades: Formatting, Voice & Conversational Intelligence Harness
- **Status**: `VERIFIED`
- **Dependencies**: Phase 2 (VERIFIED)
- **Key Deliverables**:
  - **GFM Table & Response Formatting**: Auto-formatting for tables, comparisons, checklists, code-only, and Mermaid diagrams with responsive React renderers.
  - **Voice Input (STT) & Voice Output (TTS)**: Microphone audio recording with timer UI, `/voice/transcribe`, and zero-cost Web Speech API with backend speech text cleaning.
  - **Centralized Context Builder**: `ContextBuilder` service assembling structured system prompts, enforcing anti-robotic rules ("Based on stored data" eliminated), and managing sliding-window token budgets.
  - **Configurable Assistant Personality**: `AssistantPersonalityConfig` and `PersonalityService` with settings UI for communication style, formality, detail level, and memory integration modes.
  - **Behavioral Test Suite**: 14 dedicated tests in `test_assistant_intelligence.py` covering all 10 behavioral scenarios.

---

### Phase 3: Tool Execution & Human-in-the-Loop Approvals
- **Status**: `VERIFIED`
- **Dependencies**: Phase 2 (VERIFIED)
- **Key Deliverables**:
  - **Centralized Tool Execution Engine**: Provider-independent `ToolExecutionEngine`, `ToolRegistry`, and `BaseTool` supporting native tools, external APIs, and MCP servers.
  - **Three-Tier Permission Architecture**:
    - *Level 1 (Safe)*: Auto-executes under configured permissions (`get_system_time`, `calculate`, `text_processor`, `json_validator`, `file_searcher`).
    - *Level 2 (Sensitive)*: Explicit user approval required by default (`file_writer`).
    - *Level 3 (Critical)*: Explicit action-specific confirmation required (`file_deleter`).
  - **Human-in-the-Loop Approval Manager (`ApprovalManager`)**:
    - Atomic, race-safe state transitions (`pending` -> `approved` / `rejected` / `cancelled`).
    - Expiration management and canonical SHA-256 argument hashing (`arguments_hash`) preventing parameter tampering between approval and execution.
  - **MCP Integration Layer (`McpClient`, `McpServerManager`)**:
    - Tool discovery from stdio / HTTP JSON-RPC MCP servers, schema normalization, connection health tracking, and `PromptInjectionGuard` output isolation.
  - **Native Built-in Sandboxed Tools**:
    - 8 core tools registered: clock, math calculator, text processor, JSON validator, path-traversal protected file reader/searcher/writer/deleter in `workspace_storage/`.
  - **Conversational Multi-Round Execution**:
    - Streaming SSE chat with tool call detection, multi-round execution (max 5 rounds), buffer reset, and round-2 LLM synthesis.
  - **Full Frontend Tooling & Approvals Dashboards**:
    - `ApprovalsView.tsx` (metrics, filter tabs, details modal, confirmation dialogs).
    - `ToolsView.tsx` (tool catalog, JSON schema viewer, test runner, execution history logs, MCP server manager).
    - `ActivityLogsView.tsx` (execution audit log).
    - Interactive in-chat Approval Cards in `ChatMessage.tsx`.
- **Acceptance Criteria**:
  - [x] Provider-independent tool execution engine operational with input schema validation.
  - [x] Three-tier permission architecture actively enforces Safe, Sensitive, and Critical boundaries.
  - [x] Atomic state transitions prevent race conditions and duplicate executions on approval.
  - [x] SHA-256 canonical argument hashing guarantees tamper resistance.
  - [x] MCP tools discoverable and invokable with prompt injection defenses.
  - [x] Native tools sandbox isolated with path-traversal protection.
  - [x] Multi-round conversational tool execution loops with safety limits.
  - [x] Approvals, Tools, and Activity Logs UI functional with real PostgreSQL tables.
  - [x] All 90 backend tests pass (100%); frontend production build compiles with 0 errors.

---

### Phase 4: Proactive Background Automations & External Integrations
- **Status**: `NOT_STARTED`
- **Dependencies**: Phase 3 (VERIFIED)
- **Key Deliverables**:
  - **Scheduled Automations Engine**: Cron and interval-based recurring job scheduler with Celery Beat.
  - **Proactive Notification & Alert System**: Background trigger alerts delivering proactive insights to user.
  - **Third-Party OAuth Connectors**: Secure credential flows for Google Workspace (Docs, Gmail, Calendar) and GitHub.
  - **System Audit & Compliance Exporter**: Comprehensive security logs and data export tools.
