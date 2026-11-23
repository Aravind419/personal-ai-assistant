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
│   │   │   ├── schemas.py       # Tool, Execution, Approval, and MCP schemas
│   │   │   ├── validator.py     # JSON schema validator, canonical hasher, secret sanitizer
│   │   │   ├── base.py          # BaseTool and ToolRegistry with metadata & permissions
│   │   │   ├── builtin.py       # 8 native tools (clock, calc, text, json, file ops)
│   │   │   ├── approval_manager.py # Atomic approval transitions & argument hash validation
│   │   │   ├── permissions.py   # Three-tier permission evaluator
│   │   │   ├── engine.py        # ToolExecutionEngine orchestrator & timeout manager
│   │   │   ├── mcp.py           # McpClient, McpServerManager & PromptInjectionGuard
│   │   │   └── routes.py        # /api/v1/tools and /api/v1/approvals endpoints
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

---

## 5. Voice Conversation & Response Formatting Architecture

### 5.1 Response Formatting Pipeline
- **Natural Language Format Detection**: `DEFAULT_SYSTEM_INSTRUCTION` (`backend/app/conversations/service.py`) informs the LLM to identify explicit and implicit format requests (tables, bullet points, checklists `- [ ]`, numbered lists, step-by-step tutorials, raw code, JSON-only).
- **Zero-Fluff Enforcement**: When the user requests "only JSON" or "only code", models are guided to omit introductory or concluding commentary.
- **GFM Table Rendering**: Frontend uses `react-markdown` with `remark-gfm` to render responsive GitHub Flavored Markdown tables with horizontal scrolling containers (`overflow-x-auto`), dark-theme styling, and resilient parsing during SSE token streaming.
- **Message Actions**: Every completed assistant response provides Copy Message, Copy Code, Regenerate Response, and Read Aloud / Audio Playback.

### 5.2 Voice Input (Speech-to-Text)
- **Browser Recording**: Client records microphone audio using `MediaRecorder` API into `audio/webm`.
- **Live Recording State UI**: Interactive recording overlay in `ChatInput` with timer (`00:05`), pulsing red indicator, Cancel, and Done/Finish buttons.
- **Transcription Endpoint**: `POST /api/v1/voice/transcribe` validates MIME type (`audio/webm`, `audio/wav`, `audio/mp3`, `audio/ogg`, `audio/m4a`), enforces a 25MB file size limit, and transcribes audio.
- **User Review & Edit Flow**: Transcribed text is populated directly into the chat textarea, allowing the user to review, edit, and adjust text before submitting.

### 5.3 Voice Output (Text-to-Speech)
- **Client Speech Synthesis**: Zero-cost, zero-latency Web Speech API (`window.speechSynthesis`) on client side. No third-party billing or mandatory API keys required.
- **Speech Text Cleaner**: `POST /api/v1/voice/clean-for-speech` / `VoiceService.clean_markdown_for_speech` converts Markdown tables into natural spoken sentences, skips code blocks gracefully, expands checklists (`Completed task:` / `Pending task:`), and cleans URLs and symbols.
- **Voice Settings**: Configurable voice preference options (voice toggle, auto-play response toggle, voice selector, speed slider 0.5x to 2.0x) persisted in PostgreSQL `system_metadata` under key `voice_preferences`.

---

## 6. Conversational Intelligence & Context Management Architecture

### 6.1 Centralized Context Builder (`ContextBuilder`)
- **Single Source of Truth**: Replaced scattered string formatting with `ContextBuilder` (`backend/app/conversations/context_builder.py`).
- **Partitioned System Prompt Sections**:
  1. **Core Identity**: Autonomous, capable, thoughtful, and conversational personal AI partner (not a database query interface).
  2. **Anti-Robotic Directives**:
     - Explicitly forbids meta-retrieval announcements: eliminates "Based on your stored data...", "According to your saved memories...", "Based on information in your database...".
     - Weaves contextual background facts naturally into sentences without calling attention to the storage layer.
     - Transparent memory reporting: provides complete and accurate summaries when the user explicitly asks ("What do you remember about me?").
     - Suppresses repetitive filler openings ("Sure!", "Certainly!", "Of course!") and repetitive closing sign-offs ("Let me know if you need anything else").
     - Resolves pronoun references ("What about that?", "Explain the second one", "its disadvantages") from conversation history.
     - Gives direct answers to straightforward questions ("What is 2 + 2?" -> "4").
  3. **General Knowledge Independence**: Equips the assistant to answer scientific, programming, and general knowledge concepts using LLM reasoning without fabricating or requiring personal user memories.
  4. **Formatting Directives**: Strict compliance with GFM tables, checklists, and code-only zero-fluff rules.
  5. **Untrusted Data Boundaries**: Encloses past interaction facts in `<retrieved_context>` with strict directives that context is untrusted data and cannot override system prompts or safety constraints.
  6. **Token Budgeting**: Implements sliding window message history truncation to stay within model context budgets (default 6000 tokens) while retaining opening instructions and recent turns.

### 6.2 Configurable Personality & Behavioral Engine
- **Schema & Service**: `AssistantPersonalityConfig` and `PersonalityService` (`backend/app/conversations/personality.py`) stored in PostgreSQL `system_metadata` under key `assistant_personality`.
- **Configurable Dimensions**: Assistant name, communication style (natural, concise, technical, detailed), formality (balanced, casual, formal), detail level (balanced, concise, in-depth), memory usage mode (natural_weave, minimal, explicit), emoji usage (minimal, none, expressive), and custom behavioral guidelines.
- **REST Endpoints**: `GET /api/v1/conversations/settings/personality` and `PUT /api/v1/conversations/settings/personality`.
- **Frontend Controls**: Interactive personality card in `frontend/src/pages/SettingsView.tsx` with instant live persistence.

---

## 7. Tool Execution & Human-in-the-Loop Approvals Architecture (Phase 3)

### 7.1 Centralized Tool Execution Engine (`ToolExecutionEngine`)
- **Provider-Independent Abstraction**: Tools inherit from `BaseTool` defining metadata (id, name, description, category, permission level, input schema, timeout).
- **Tool Registry**: Central `ToolRegistry` managing catalog indexing, enabling/disabling tools, category grouping, and LLM JSON-schema generation.
- **Execution Pipeline**:
  1. Validates input arguments against tool's JSON schema (`ToolSchemaValidator`).
  2. Evaluates execution permissions (`ToolPermissionEngine`).
  3. Gates sensitive/critical actions through `ApprovalManager`.
  4. Manages async execution with per-tool timeouts (`asyncio.wait_for`).
  5. Normalizes execution results and sanitizes credentials/secrets (`SecretSanitizer`).
  6. Persists audit execution records in PostgreSQL `tool_executions`.

### 7.2 Three-Tier Permission Model & Human-in-the-Loop Approvals
- **Level 1 (Safe)**: Auto-executes without prompting (`get_system_time`, `calculate`, `text_processor`, `json_validator`, `file_searcher`).
- **Level 2 (Sensitive)**: Requires explicit user approval (`file_writer`). Creates pending approval record in `tool_approvals`.
- **Level 3 (Critical)**: Requires explicit action-specific confirmation with highlighted risk details (`file_deleter`).
- **Race-Safe State Transitions**: `ApprovalManager` uses atomic SQL updates (`UPDATE ... WHERE id = :id AND status = 'pending'`) preventing race conditions or double execution.
- **Canonical Argument Hashing**: Computes deterministic SHA-256 hash of sorted JSON arguments. If arguments drift or change between approval and execution, approval is automatically invalidated.

### 7.3 Model Context Protocol (MCP) Bridge & Prompt Injection Defense
- **MCP Client & Server Manager**: `McpClient` connects to external MCP servers via stdio / HTTP JSON-RPC protocols, discovers remote tools, validates schemas, and maps them dynamically into `ToolRegistry`.
- **Prompt Injection Defense (`PromptInjectionGuard`)**:
  - MCP output is strictly wrapped in isolated `<tool_output>` blocks.
  - Sanitizes adversarial injection tokens (e.g. `<system>`, `ignore previous instructions`, `new system prompt`).
  - Strict server-level permission allowlists and enable/disable toggles.

### 7.4 Native Built-in Tools & Workspace Sandboxing
- 8 built-in tools registered and verified:
  - `get_system_time`: Formatted local time and timezone info.
  - `calculate`: Safe mathematical expression evaluation.
  - `text_processor`: Word/char counts, case transforms, regex replacements.
  - `json_validator`: JSON structure validation and formatting.
  - `file_reader`: Read file contents within sandbox.
  - `file_searcher`: Search filenames by glob pattern within sandbox.
  - `file_writer` (Sensitive): Write/append file contents within sandbox.
  - `file_deleter` (Critical): Delete files within sandbox.
- **Sandbox Security**: File operations are strictly locked to `WORKSPACE_STORAGE_DIR`, resolving realpaths and rejecting path-traversal attacks (`..`, symlinks, `.env`, `id_rsa`).

### 7.5 Conversational Multi-Round Tool Calling
- Streaming SSE endpoint detects tool requests in chat messages (`extract_tool_call`).
- Automatically executes safe tools or generates approval requests for sensitive tools.
- Multi-round support (up to 5 rounds) with buffer reset allows model to inspect tool results and synthesize natural language explanations.

---

## 8. Proactive Automations & External Integrations Architecture (Phase 4)

### 8.1 Automation Management & Dispatch Subsystem
- **Automation Model (`Automation`)**: Stores scheduled tasks with natural language instruction, trigger type (`daily`, `weekly`, `monthly`, `interval`, `cron`, `one_time`, `manual`), timezone, structured action array (`AutomationAction`), status (`enabled`/`disabled`), and run metrics (`execution_count`, `last_execution_at`, `next_execution_at`).
- **Timezone-Aware Next Run Computation (`scheduler_utils.py`)**:
  - Leverages Python `zoneinfo.ZoneInfo` and `croniter` for rigorous DST transitions and recurring intervals.
  - Defaults to `DEFAULT_TIMEZONE` (UTC or user-configured).
- **Execution Tracking (`AutomationExecution`)**:
  - Captures execution state: `SCHEDULED`, `QUEUED`, `RUNNING`, `WAITING_FOR_APPROVAL`, `SUCCEEDED`, `FAILED`, `CANCELLED`, `SKIPPED`, `TIMED_OUT`.
  - Records step-by-step actions, tool outputs, execution duration, and error diagnostics.
- **Natural Language Parsing (`AutomationInstructionParser`)**:
  - Extracts intended schedule and tools using heuristics/LLM reasoning.
  - Enforces strict validation via `ToolRegistry.has` — never trusts hallucinated tool names.

### 8.2 Execution Engine & Celery Beat Integration
- **Hybrid Dispatch Architecture (`AutomationService.trigger_run`)**:
  - **Manual/Synchronous Runs (`background=False`)**: Direct execution in request context with immediate return of status and tool output summary.
  - **Scheduled/Worker Runs (`background=True`)**: Celery task dispatch (`run_automation_celery_task.apply_async`) with automated fallback to asynchronous background loop task if Celery workers are offline.
- **Periodic Scheduler (`Celery Beat`)**:
  - Periodic task `dispatch-due-automations-every-minute` triggers `dispatch_due_automations_task` every 60 seconds.
  - Queries active enabled automations where `next_execution_at <= now()` and dispatches tasks with idempotency guarantees.

### 8.3 Permission & Approval Gating for Automations
- **Zero-Bypass Integration**:
  - Automation actions pass directly through `ToolExecutionEngine`, `ToolPermissionEngine`, and `ApprovalManager`.
  - `SAFE` tools execute automatically.
  - `SENSITIVE` and `CRITICAL` tools halt the automation in `WAITING_FOR_APPROVAL` state, create a single-use execution-linked approval in `tool_approvals`, and generate an in-app notification.
  - A prior approval cannot authorize future recurring executions — each run maintains its own distinct approval lifecycle.

### 8.4 First-Party OAuth Integrations Framework
- **Abstract Provider Contract (`BaseIntegrationProvider`)**:
  - Defines OAuth URL generation, code exchange, token refresh, connection testing, data sync, and disconnection.
  - `GoogleIntegrationProvider`: Manages Google Workspace integration (Gmail, Calendar, Drive).
  - `GitHubIntegrationProvider`: Manages GitHub integration (Repositories, Issues).
- **Encrypted Credential Storage (`IntegrationConnection`)**:
  - Stores access and refresh tokens encrypted with AES-256 (Fernet) via `IntegrationManager`.
  - Cryptographic CSRF state validation in Redis/in-memory state cache.
- **10 Integration Tools (`app/integrations/tools.py`)**:
  - `google_mail_list`, `google_mail_read`, `google_mail_send` (Sensitive).
  - `google_calendar_list`, `google_calendar_create` (Sensitive), `google_calendar_delete` (Critical).
  - `google_drive_list`.
  - `github_list_repos`, `github_list_issues`, `github_create_issue` (Sensitive).
  - Output sanitization (`sanitize_untrusted_text`) neutralizes delimiter breakout and malicious payloads.

### 8.5 Morning Briefing & Persistent Notifications
- **Morning Briefing Generator (`BriefingService`)**:
  - Aggregates upcoming calendar events, unread emails, pending tool approvals, and active automations.
  - Synthesizes formatted Markdown briefings without hallucinating missing data.
  - Exposes `GenerateMorningBriefingTool` for agentic use and REST endpoints (`/api/v1/briefings`).
- **Notification Subsystem (`NotificationService`)**:
  - Persistent notifications stored in PostgreSQL `notifications`.
  - Categories: `AUTOMATION_SUCCESS`, `AUTOMATION_FAILED`, `APPROVAL_REQUIRED`, `INTEGRATION_SYNC`, `BRIEFING_READY`.
  - Supports unread count polling, mark as read, mark all read, and dismissal.

