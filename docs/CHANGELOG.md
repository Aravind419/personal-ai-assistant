# Project Changelog

All notable changes, milestone completions, and architectural modifications to the **Personal AI Assistant** project will be documented in this file chronologically.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.2.0] - 2026-11-22 - Phase 1 Basic AI Agent Complete

### Added
- **AI Provider Abstraction Layer**:
  - `BaseLLMProvider` abstract interface (`backend/app/providers/base.py`) with unified schemas for streaming, non-streaming, model discovery, and connection testing.
  - Centralized `ProviderRegistry` (`backend/app/providers/registry.py`) providing dynamic adapter discovery and active provider dispatch.
  - Complete, functional OpenRouter provider adapter (`backend/app/providers/adapters/openrouter.py`) supporting real-time Server-Sent Events (SSE) streaming, credential verification, model listing, and error normalization.
  - Prepared adapter stubs for future providers: NVIDIA NIM (`app/providers/adapters/nvidia.py`) and local Ollama (`app/providers/adapters/ollama.py`).
  - Provider management endpoints under `/api/v1/providers`: listing, updating credentials, testing connections, and activating default providers.
- **Database & Persistence**:
  - Relational models for `ProviderConfiguration`, `Conversation`, and `Message` in `backend/app/models/`.
  - Alembic migration `002_conversations_and_providers.py` adding all Phase 1 tables with foreign keys and cascade rules.
  - Symmetric encryption for API keys using Fernet with derived keys from `SECRET_KEY` (`backend/app/core/security.py`).
  - Switched SQLAlchemy connection pool to `NullPool` in `backend/app/database/connection.py` for safe asynchronous event loop lifecycle across test and request boundaries.
- **Conversations & Streaming Chat Engine**:
  - Conversation management service (`backend/app/conversations/service.py`) supporting conversation threads, titles, model switching, and message persistence.
  - Real-time SSE streaming endpoint `POST /api/v1/conversations/{id}/messages` that streams tokens directly to the client and persists user and assistant messages in PostgreSQL.
- **Tool Calling Architecture**:
  - Extensible backend tool execution foundation (`backend/app/tools/base.py`) with parameter validation and controlled execution.
  - Baseline built-in safe tools: `SystemClockTool` and `CalculatorTool` (`backend/app/tools/builtin.py`).
- **Frontend Chat & Settings Experience**:
  - Interactive **Chat View** (`frontend/src/pages/ChatView.tsx`) with conversation history sidebar, new thread creation, inline renaming, thread deletion, and model switching.
  - Streaming token rendering with pulsing cursor, auto-scroll, and abort/stop generation controls.
  - Markdown message rendering with custom syntax-highlighted code blocks and one-click copy (`frontend/src/components/chat/ChatMessage.tsx`).
  - Interactive **Provider Settings View** (`frontend/src/pages/SettingsView.tsx`) with masked API key inputs, password visibility toggle, dynamic model selection, live connection testing, and prepared cards for NVIDIA and Ollama.
  - Activated Chat and Settings navigation items in the application sidebar.
- **Automated Tests & Quality**:
  - Added 13 new backend automated tests across `test_providers.py`, `test_security.py`, `test_conversations.py`, `test_chat_stream.py`, and `test_tools.py` (22 total tests passing).
  - Verified clean TypeScript build (`tsc -b && vite build`) with zero errors.
  - Verified browser workflows using Playwright MCP.

---

## [0.1.0] - 2026-11-22 - Phase 0 Foundation Complete

### Added
- **Configuration & Environment**:
  - Robust boolean validator for `DEBUG` setting handling non-standard environment values (`release`, `debug`, `0`, `1`).
- **Backend Architecture**:
  - FastAPI application entrypoint with lifespan event handlers and graceful degraded startup (`backend/app/main.py`).
  - Modular API router mounted under `/api/v1/` (`backend/app/api/router.py`).
  - Diagnostic endpoints: `/api/v1/health`, `/api/v1/health/db`, and `/api/v1/info`.
  - Pydantic v2 settings configuration with secret redaction (`backend/app/core/config.py`).
  - Structured logging with regex password masking (`backend/app/core/logging.py`).
  - Centralized RFC-compliant exception handling (`backend/app/core/exceptions.py`).
  - Asynchronous SQLAlchemy 2.x engine and request-scoped session dependency `get_db` (`backend/app/database/`).
  - Database ping probe utility measuring query latency (`backend/app/database/connection.py`).
  - Declarative base with `TimestampMixin` and `SystemMetadata` table model (`backend/app/models/system.py`).
  - Alembic asynchronous migration pipeline (`backend/alembic/`) with migration `001_initial_foundation.py` and pgvector extension hook.
  - Automated test suite with 9 passing pytest tests covering health, config, exceptions, and DB connectivity.
- **Frontend Architecture**:
  - React 19 + TypeScript 5.9+ frontend bootstrapped with Vite 8.
  - Tailwind CSS v4 styling with dark theme palette and responsive breakpoints.
  - Application shell (`AppShell.tsx`, `Sidebar.tsx`, `Header.tsx`) with 11 navigation modules.
  - Live diagnostic overview dashboard (`DashboardOverview.tsx`) with real-time FastAPI health cards, database ping latency, architectural stack summary, and raw telemetry feed.
  - Phase-gated placeholders (`PlaceholderView.tsx`) for unbuilt modules.
  - Common UI feedback components: `StatusBadge`, `LoadingState`, `ErrorState`, `EmptyState`.
  - Typed API client (`api.ts`, `healthService.ts`) with request timeouts and standardized error extraction.
- **Infrastructure & Containerization**:
  - Docker Compose service definition (`docker-compose.yml`) for PostgreSQL 16 with pgvector extension and automated container healthcheck.
  - Root, backend, and frontend `.env.example` templates.
- **Documentation & Continuity System**:
  - Comprehensive operating guidelines in `AGENTS.md`.
  - Core system documentation in `docs/`.
