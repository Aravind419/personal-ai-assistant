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
| Phase 1: Chat Interface & Agent State Foundation (NOT_STARTED)                          |
| - OpenAI provider abstraction + LangGraph agent state loop + Chat UI + Activity Logs    |
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
| - OAuth connectors (Google/GitHub) + Cron/event automations + Settings & System Audit    |
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
- **Acceptance Criteria**:
  - [x] Backend responds to `/api/v1/health` and `/api/v1/info`.
  - [x] Database ping measures latency accurately and reports degraded state if database is offline.
  - [x] Frontend runs with responsive sidebar, dynamic status pills, and empty/error states.
  - [x] Secrets are completely redacted from all logging pipelines.

---

### Phase 1: Chat Interface & Agent State Foundation
- **Status**: `NOT_STARTED`
- **Dependencies**: Phase 0 (VERIFIED)
- **Key Deliverables**:
  - **OpenAI Provider Abstraction**: Modular LLM provider layer (`backend/app/providers/`) isolating the agent core from model API vendors.
  - **Agent State Graph**: Initial LangGraph graph with conversation history checkpointing, session management, and state transitions.
  - **Streaming Chat API**: SSE (Server-Sent Events) or WebSocket endpoint for real-time token streaming.
  - **Chat Interface**: Fully interactive React chat interface with Markdown rendering, syntax highlighting, and conversation history.
  - **Activity Logs**: Centralized activity logging module tracking user prompts, agent reasoning events, and system notifications.
  - **Initial Settings View**: Basic configuration view for LLM model parameters and environment keys.
- **Acceptance Criteria**:
  - [ ] User can send prompts and receive streamed LLM responses in real-time.
  - [ ] Conversations persist across browser reloads via database session state.
  - [ ] System events and agent executions produce structured logs visible in the Activity Logs view.
  - [ ] All new backend and frontend tests pass cleanly.

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
- **Acceptance Criteria**:
  - [ ] Conversations automatically extract and store semantic facts in pgvector.
  - [ ] Agent recalls relevant memories in subsequent chat sessions.
  - [ ] Background tasks execute asynchronously without blocking API threads.

---

### Phase 3: Tool Execution & Human-in-the-Loop Approvals
- **Status**: `NOT_STARTED`
- **Dependencies**: Phase 2 (VERIFIED)
- **Key Deliverables**:
  - **Tool Registry**: Dynamic registry for registering, discovering, and executing local tools (filesystem, web search, shell, Python sandbox).
  - **MCP Bridge**: Model Context Protocol client for connecting external MCP servers.
  - **Human-in-the-Loop Approval Engine**: Gatekeeper system requiring explicit user confirmation before executing potentially destructive or sensitive actions.
  - **Approvals & Tools UI**: Dedicated interface to inspect available tools, view pending approval requests, and grant/deny permissions.
- **Acceptance Criteria**:
  - [ ] Agent correctly invokes registered tools to answer questions requiring external state.
  - [ ] Destructive tools (file writes, commands) halt execution and prompt for approval in the Approvals UI.
  - [ ] Actions execute only after explicit user approval.

---

### Phase 4: Proactive Automations & External Integrations
- **Status**: `NOT_STARTED`
- **Dependencies**: Phase 3 (VERIFIED)
- **Key Deliverables**:
  - **Third-Party Connectors**: OAuth 2.0 integrations with Google Workspace (Calendar, Gmail), GitHub, etc.
  - **Automations Engine**: Event-driven and cron-scheduled proactive agent routines (e.g. daily morning briefing, unread email summary).
  - **Integrations & Automations UI**: Configuration dashboards for managing OAuth tokens and automation rules.
  - **Full System Security Audit**: Penetration review, credential storage review, and final production hardening.
- **Acceptance Criteria**:
  - [ ] User can link third-party accounts securely via OAuth.
  - [ ] Proactive automations run on schedule and push notifications or summary items to the dashboard.
  - [ ] Comprehensive documentation and operational runbooks finalized.
