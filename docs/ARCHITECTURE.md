# Personal AI Agent — System Architecture

## 1. System Vision & Purpose

The Personal AI Agent is a long-term engineering initiative designed to build a unified, autonomous personal assistant. Unlike ephemeral chat bots or multi-tenant SaaS products, this system is engineered for a **single personal user**, emphasizing persistent long-term memory, deterministic tool integrations, proactive background automation, human-in-the-loop permission boundaries, and hybrid local/cloud deployment.

```
                      +-------------------------------------------------+
                      |            React 19 + TypeScript Frontend        |
                      |   (Vite, Tailwind v4, Chat, Settings, Overview) |
                      +------------------------+------------------------+
                                               | HTTP / REST & SSE Stream
                                               v
                      +-------------------------------------------------+
                      |              FastAPI Backend Engine             |
                      |  (Modular API, Providers, Conversations, Tools) |
                      +------------------------+------------------------+
                                               |
                   +---------------------------+---------------------------+
                   |                                                       |
                   v                                                       v
      +-------------------------+                             +-------------------------+
      |  LLM Provider Adapter   |                             |   PostgreSQL Database   |
      |   (OpenRouter Active)   |                             | (Conversations, Messages|
      |  [NVIDIA/Ollama Ready]  |                             |  Provider Config, Vector)
      +-------------------------+                             +-------------------------+
                   |                                                       |
                   v                                                       v
      +-------------------------+                             +-------------------------+
      |  Controlled Tool Engine |                             |  (Phase 2+) pgvector &  |
      |  (Clock, Calculator)    |                             |  Redis/Celery Workers   |
      +-------------------------+                             +-------------------------+
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
| **Vector Engine** | pgvector (Active) | Single-database storage eliminating dual-database synchronization issues between vectors and relational records. |
| **Embedding Provider** | Provider-Independent Interface | Pluggable embedding providers (`BaseEmbeddingProvider`) with deterministic `LocalSemanticEmbeddingProvider` (zero downloads) and OpenRouter adapter. |
| **Semantic Memory** | Extraction & Retrieval Pipeline | Asynchronous extraction, secret sanitization, deduplication (>= 0.85), superseding conflict handling, and `<retrieved_context>` prompt injection. |
| **Background Tasks** | Redis + Celery + Async Fallback | Reliable task queue running in Docker container with local asynchronous fallback, retries, and sanitized error persistence. |
| **AI Provider** | Provider-Independent Adapter Architecture | Isolates core agent from model vendors. OpenRouter implemented as initial gateway; NVIDIA & Ollama prepared. |
| **Model Registry** | Central Model Registry & Policy Engine | Central catalog managing pricing categories (`free`/`paid`), capabilities, context limits, and token cost calculation. |
| **Operational Modes** | Free-Only, Paid-Enabled, Manual | Strict guardrails: Free-Only mode strictly prevents executing or falling back to paid models. |
| **Failover Strategy** | Multi-Candidate Fallback Chains | Automatically reroutes requests to alternative models on rate limits (429) or provider outages with client notices. |
| **Execution Telemetry**| Model Metrics & Cost Tracking | Captures token volume, estimated USD costs, latency, and error types in `model_execution_metrics`. |
| **Streaming** | Server-Sent Events (SSE) | Unidirectional low-overhead token delivery with standard browser `AbortController` cancellation. |
| **Credential Security** | Fernet Symmetric Encryption at Rest | API keys encrypted with keys derived from master `SECRET_KEY`; never exposed in API responses. |
| **Tool Execution** | Controlled Backend Dispatch | Parameter validation via JSON Schema; no arbitrary shell or unrestricted computer access. |
| **Future Tasks** | Redis + Celery (Phase 2+) | Reliable background task queue for long-running workflows, automated periodic audits, and proactive triggers. |

---

## 3. Directory Layout

```
personal-ai-assistent/
├── .env.example                 # Root environment variables reference
├── .gitignore                   # Multi-tier ignore rules (Node, Python, Postgres, secrets)
├── docker-compose.yml           # PostgreSQL + pgvector container configuration
├── README.md                    # Project overview & quickstart guide
├── docs/
│   ├── ARCHITECTURE.md          # Complete architectural specification (this file)
│   ├── CHANGELOG.md             # Chronological release log
│   ├── DECISIONS.md             # Architectural Decision Records (ADRs)
│   ├── DEVELOPMENT.md           # Setup and developer workflow instructions
│   ├── PROJECT_OVERVIEW.md      # Project vision, capabilities, user model
│   ├── PROJECT_STATUS.md        # Session continuity record and next tasks
│   ├── ROADMAP.md               # Implementation phases and deliverables
│   ├── SECURITY.md              # Security policies and credential rules
│   └── phase-0.md               # Phase 0 deliverables & verification report
├── backend/
│   ├── .env.example             # Backend-specific environment template
│   ├── pyproject.toml           # Modern Python packaging configuration (uv/pip)
│   ├── requirements.txt         # Pinned production and test dependencies
│   ├── alembic.ini              # Database migration configuration
│   ├── alembic/
│   │   ├── env.py               # Async Alembic execution environment
│   │   ├── script.py.mako       # Migration template script
│   │   └── versions/
│   │       ├── 001_initial_foundation.py  # Baseline table & pgvector hook
│   │       └── 002_conversations_and_providers.py # Phase 1 tables
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Application entrypoint, lifespan, CORS, and routers
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── router.py        # Centralized /api/v1 router
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Pydantic BaseSettings environment validation
│   │   │   ├── logging.py       # Structured logging with secret redaction
│   │   │   ├── security.py      # Fernet symmetric encryption for credentials
│   │   │   └── exceptions.py   # Centralized RFC-style error handlers
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # SQLAlchemy DeclarativeBase and TimestampMixin
│   │   │   ├── connection.py    # Async engine initialization (NullPool)
│   │   │   └── session.py       # AsyncSession dependency injection
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── system.py        # SystemMetadata foundation table
│   │   │   ├── provider.py      # ProviderConfiguration table
│   │   │   └── conversation.py  # Conversation and Message tables
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # Abstract BaseLLMProvider interface
│   │   │   ├── schemas.py       # Normalized ChatMessage, Completion, Model schemas
│   │   │   ├── registry.py      # Dynamic ProviderRegistry
│   │   │   ├── service.py       # Provider business logic & credential encryption
│   │   │   ├── routes.py        # /api/v1/providers REST endpoints
│   │   │   └── adapters/
│   │   │       ├── openrouter.py # Full OpenRouter SSE & completions adapter
│   │   │       ├── nvidia.py     # Prepared NVIDIA NIM adapter stub
│   │   │       └── ollama.py     # Prepared local Ollama adapter stub
│   │   ├── conversations/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py       # Conversation & message schemas
│   │   │   ├── service.py       # Thread management & SSE chat streaming service
│   │   │   └── routes.py        # /api/v1/conversations REST & SSE endpoints
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # Re-export of Memory model
│   │   │   ├── schemas.py       # Pydantic schemas for CRUD and search
│   │   │   ├── embeddings.py    # BaseEmbeddingProvider and LocalSemanticEmbeddingProvider
│   │   │   ├── repository.py    # Data access layer and pgvector HNSW cosine search
│   │   │   ├── service.py       # Memory business service and multi-factor ranking
│   │   │   ├── extraction.py    # Conversation extraction and conflict superseding
│   │   │   ├── retrieval.py     # Prompt context builder and injection isolation
│   │   │   └── routes.py        # /api/v1/memories REST endpoints
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # Re-export of BackgroundTask model
│   │   │   ├── schemas.py       # Task schemas and status enums
│   │   │   ├── celery_app.py    # Celery application and task definitions
│   │   │   ├── service.py       # Task dispatch, cancellation, retry, and async fallback
│   │   │   └── routes.py        # /api/v1/tasks REST endpoints
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # BaseTool and ToolRegistry
│   │   │   └── builtin.py       # SystemClockTool and CalculatorTool
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
│       ├── conftest.py          # Session-scoped test fixtures
│       ├── test_config.py       # Environment parsing & sanitization tests
│       ├── test_exceptions.py   # Centralized error handler tests
│       ├── test_health.py       # API endpoints & DB probe tests
│       ├── test_security.py     # Fernet encryption & masking tests
│       ├── test_providers.py    # Provider registry & adapter tests
│       ├── test_conversations.py# Conversations CRUD & cascading tests
│       ├── test_chat_stream.py  # SSE streaming & message persistence tests
│       └── test_tools.py        # Tool registry & execution tests
└── frontend/
    ├── .env.example             # Frontend environment template
    ├── package.json             # Node dependencies and scripts
    ├── tsconfig.json            # Strict TypeScript configuration
    ├── vite.config.ts           # Vite + Tailwind CSS configuration
    ├── index.html               # Entry HTML shell
    └── src/
        ├── index.css            # Tailwind CSS root rules
        ├── main.tsx             # React root mount
        ├── App.tsx              # Root application router and shell container
        ├── config/
        │   └── env.ts           # Type-safe environment variable access
        ├── types/
        │   ├── api.ts           # Health & diagnostic interfaces
        │   ├── chat.ts          # Conversation & Message interfaces
        │   ├── provider.ts      # Provider configuration & model interfaces
        │   └── navigation.ts    # Navigation configuration interfaces
        ├── services/
        │   ├── api.ts           # Fetch API wrapper with timeout & error handling
        │   ├── healthService.ts # Health & diagnostics client service
        │   ├── providerService.ts # Provider configuration client
        │   ├── conversationService.ts # Conversation thread management client
        │   └── chatStreamService.ts # SSE streaming reader
        ├── components/
        │   ├── common/          # StatusBadge, LoadingState, ErrorState, EmptyState, PlaceholderView
        │   ├── layout/          # Header, Sidebar, AppShell
        │   └── chat/            # ChatMessage (Markdown), ChatInput, ConversationSidebar
        └── pages/
            ├── DashboardOverview.tsx # Foundation diagnostic dashboard
            ├── ChatView.tsx          # Real-time streaming chat page
            ├── MemoryView.tsx        # Semantic long-term memory explorer
            ├── TasksView.tsx         # Background task worker dashboard
            └── SettingsView.tsx      # AI Provider configuration page
```

---

## 4. Security Principles

1. **Strict Credential Sanitization**:
   - Secrets (`SECRET_KEY`, database passwords) are never logged. The backend's `sanitized_database_url` utility redacts user:password credentials before logging connection targets.
2. **Encryption at Rest**:
   - API keys are encrypted at rest using Fernet symmetric encryption with 256-bit derived keys from `SECRET_KEY`.
   - Saved keys are never returned in plaintext in API responses (only masked strings e.g. `sk-or-••••••••abcd`).
3. **Environment Variable Isolation**:
   - Frontend and backend configurations are strictly isolated. No backend secret or private token is prefixed with `VITE_` or leaked to client bundles.
4. **Restricted CORS Policy**:
   - Cross-Origin Resource Sharing is restricted explicitly to configured development and production hosts (`CORS_ORIGINS`).
5. **Sandboxed Tool Calling**:
   - Agent tool execution is strictly validated via JSON Schema on the backend. No arbitrary shell execution or unrestricted filesystem access is allowed.
6. **Memory Context Isolation & Prompt Defense**:
   - Retrieved memories are wrapped strictly inside `<retrieved_context>` tags and labeled explicitly as unverified contextual background rather than system instructions.
   - The memory extraction pipeline actively detects and discards passwords, API keys, Bearer tokens, and financial identifiers.
7. **Task Error Sanitization**:
   - Background task failure traces are sanitized before persistence and API serialization, preventing leakage of internal execution environments or credentials.
