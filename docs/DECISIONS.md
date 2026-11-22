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

---

## ADR-007: Provider-Independent Architecture & OpenRouter as Initial Adapter
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Directly coupling the assistant to a single LLM vendor makes provider migration, local inference (Ollama), and multi-provider failover difficult. OpenRouter provides a single unified interface to 100+ commercial and open models (OpenAI, Anthropic, Meta, Google, DeepSeek).
- **Decision**:
  Implement an abstract `BaseLLMProvider` interface and a `ProviderRegistry`. Completely implement OpenRouter as the first functional provider, while scaffolding adapter stubs for NVIDIA NIM and Ollama.
- **Consequences**:
  - The core chat engine communicates exclusively through normalized `ChatCompletionRequest` and `ChatStreamChunk` schemas.
  - Adding future providers requires only authoring a single adapter subclass without altering chat or conversation code.

---

## ADR-008: Symmetric Encryption at Rest for API Credentials
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Storing user API keys in plaintext in PostgreSQL poses an unacceptable risk if database backups or dumps are accessed.
- **Decision**:
  Encrypt API keys before persisting to `provider_configurations` using Fernet symmetric encryption with a 256-bit key derived from the master `SECRET_KEY` held outside the database.
- **Consequences**:
  - API keys are never stored in plaintext in the database.
  - Frontend responses only receive masked strings (e.g. `sk-or-••••••••abcd`) and a boolean flag `has_api_key`.

---

## ADR-010: Central Model Registry & Provider-Independent Multi-Model Selection
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Hardcoding models or tying model choices to hardcoded strings within agent logic prevents seamless model switching, causes unexpected billing charges, and obscures model capabilities (pricing, context window, tools).
- **Decision**:
  Implement a central `CentralModelRegistry` that classifies models into `PricingCategory.FREE` and `PricingCategory.PAID`, tracks context limits and capabilities, enriches live catalogs from OpenRouter, and computes token costs. All model resolution in the agent flows through this central abstraction.
- **Consequences**:
  - The core agent never references vendor-specific model strings directly.
  - Adding new models or custom endpoints updates the registry without touching conversation services.

---

## ADR-011: Strict Operational Modes (Free-Only vs Paid-Enabled) & Fallback Chains
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Users developing or experimenting with personal agents must never suffer unexpected billing charges from automatic model fallbacks or misconfigured queries.
- **Decision**:
  Implement three distinct operational modes: `free_only`, `paid_enabled`, and `manual`. In `free_only` mode, the backend strictly rejects any paid model requests and purges paid models from fallback chains. Configurable fallback chains automatically switch to backup free models when rate limits (429) or outages occur.
- **Consequences**:
  - Absolute zero-cost guarantee during development when `free_only` is active.
  - Resilience against rate limits and transient provider outages through automatic failover.

---

## ADR-012: Real-Time Token Usage, Cost & Performance Telemetry
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Managing LLM costs and diagnosing model latency requires persistent telemetry per request and aggregate visibility.
- **Decision**:
  Create the `model_execution_metrics` table to capture prompt tokens, completion tokens, total tokens, estimated cost in USD, and latency in milliseconds for every model call (successful, fallback, or error). Expose aggregate statistics via `/api/v1/models/metrics` and display them in the Settings dashboard.
- **Consequences**:
  - Transparent audit trail of token consumption and estimated spending.
  - Instant visibility into model response latency and error rates across providers.

---

## ADR-013: Deterministic & Provider-Independent Embedding Architecture
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Requiring a commercial paid embedding API (e.g. OpenAI `text-embedding-3-small`) violates the project's zero-cost development principle. Conversely, automatically downloading massive multi-gigabyte HuggingFace models causes unexpected network delays, storage bloating, and potential failure in offline development environments.
- **Decision**:
  Implement a provider-independent `BaseEmbeddingProvider` interface with an `EmbeddingRegistry`. By default, use `LocalSemanticEmbeddingProvider`, which computes normalized 384-dimensional dense vectors using subword and character n-gram hashing and term weighting. Support `OpenRouterEmbeddingProvider` as a pluggable cloud alternative.
- **Consequences**:
  - Zero required API keys, zero network downloads, and sub-millisecond execution.
  - Semantic vector similarity is fully supported in PostgreSQL pgvector via HNSW index.
  - Future embedding models can be added cleanly via the provider registry.

---

## ADR-014: Asynchronous Memory Extraction with Deduplication & Historical Superseding
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Chat responses must never be delayed by memory extraction or vector generation. Furthermore, conversation facts evolve over time (e.g., "User is learning React" followed later by "User finished React and is learning Flutter"). Blindly appending duplicate or conflicting memories pollutes vector search and degrades prompt quality.
- **Decision**:
  Schedule memory extraction as an asynchronous background task immediately after assistant message persistence. The extraction pipeline evaluates semantic similarity (>= 0.85); when superseding facts are detected, the existing memory is updated and previous versions are preserved in `metadata_json.history`.
- **Consequences**:
  - Chat streaming remains instant and unblocked.
  - Memory store remains concise, accurate, and free of stale contradictions.
  - Transparent audit trail of memory updates.

---

## ADR-015: Redis & Celery Background Workers with Resilient Asynchronous Fallback
- **Date**: 2026-11-22
- **Status**: Accepted
- **Context**:
  Background task execution requires durable scheduling, execution timeouts, retries, and failure visibility. However, during local development or startup, Redis or Celery worker processes may not always be booted. Crashing or dropping tasks when Celery is offline impairs developer ergonomics.
- **Decision**:
  Containerize Redis (`redis:7-alpine`) in `docker-compose.yml` and configure Celery workers with 60s soft / 120s hard timeouts and exponential backoff retries. Implement a resilient fallback in `TaskService` that executes tasks directly in the local asynchronous event loop if Celery broker dispatch is unavailable.
- **Consequences**:
  - Production-ready background queue architecture.
  - Total resilience: background tasks always execute and persist state in `background_tasks`.
  - Zero crashes or lost tasks when Redis is temporarily offline.
