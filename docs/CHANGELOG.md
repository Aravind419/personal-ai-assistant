# Project Changelog

All notable changes, milestone completions, and architectural modifications to the **Personal AI Assistant** project will be documented in this file chronologically.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.6.2] - 2026-11-23 - Critical Repair: Agent Tool Calling, Provider Function Calling, MCP Execution & Chat UI Redesign

### Added & Fixed
- **Provider-Independent Native Tool Calling & Orchestration Loop**:
  - Implemented standard OpenAI/OpenRouter function-calling payload support (`tools: [...]`, `tool_choice: "auto"`) in `backend/app/providers/adapters/openrouter.py`.
  - Added streaming delta tool-call parsing (`delta.tool_calls`) across SSE chunks.
  - Resolved tool identifier vs. descriptive name mismatch: `BaseTool.to_openai_tool_schema()` enforces clean, sanitized tool IDs matching `^[a-zA-Z0-9_-]+$`, eliminating spaces and API rejection.
  - Overhauled `ContextBuilder.format_tools_catalog()` and `TOOL_INSTRUCTIONS_SECTION` to format tools using their exact programmatic ID (`gmail_get_profile`, `get_system_time`, `calculate_expression`).
  - Added smart fuzzy and canonical snake_case normalization lookup in `ToolRegistry.get()` preventing tool lookup misses.
  - Eliminated raw tool JSON leakage in conversation bubbles: `stream_chat` buffers incoming chunks to detect tool call patterns; never emits internal tool arguments or call structures as `type: token`.
  - Implemented automatic multi-round loop: tool executes via `ToolExecutionEngine`, emits progress notifications (`assistant_status`, `tool_execution_started`, `tool_execution_completed`), feeds execution results in Round 2, and streams a clean natural-language final response.
- **Gmail Send-Test Workflow with Human Confirmation**:
  - Added `POST /api/v1/integrations/google_gmail/send-test` endpoint enforcing RFC 5322 email regex validation, active connection verification, draft previewing, and explicit human confirmation before sending real emails.
  - Added interactive "Send Test" action button on the Gmail card and a dedicated `Send Verified Test Email` modal in `IntegrationsView.tsx`.
- **Runtime MCP Server Management & Diagnostics**:
  - Added `POST /api/v1/tools/mcp/servers/{server_id}/test` endpoint executing protocol handshake initialization, discovering capabilities, measuring roundtrip latency in milliseconds, and reporting connection diagnostics.
  - Added "Test Connection" button on MCP server cards in `ToolsView.tsx`.
- **Chat UI & Responsive Sidebar Redesign**:
  - Transformed the navigation sidebar into a responsive collapsible rail (`Sidebar.tsx`), collapsing to an icon-only rail (`w-16`) on desktop with hover tooltips and expand/collapse toggle buttons in `Header.tsx`.
  - Upgraded Chat layout (`ChatView.tsx`) to a clean, spacious viewport with bottom-docked composer, auto-resizing text area, and live tool activity progress indicator.
  - Implemented expandable structured Tool Execution History cards inside `ChatMessage.tsx` rendering execution latency, tool name, parameters, and results without cluttering conversational bubbles.
- **Verification**:
  - **131 passing automated backend pytest tests** (100% pass rate).
  - Clean TypeScript compilation (`tsc -b`) and Vite production bundle generated in 1.84s.

### Added & Refactored
- **Independent Integration Services Decomposition**:
  - Replaced monolithic Google Workspace card with 8 independent, first-class services in `backend/app/integrations/google_services.py`:
    1. **Gmail** (`google_gmail`): Read, search, draft, send with approval, thread history, attachments.
    2. **Google Drive** (`google_drive`): Search, metadata, read, download, export Docs/Sheets, upload notes.
    3. **Google Calendar** (`google_calendar`): List today/window events, check availability, create meetings, delete events.
    4. **Google Docs** (`google_docs`): Read document structure, create documents via Docs v1 API.
    5. **Google Sheets** (`google_sheets`): Read range, append rows via Sheets v4 API.
    6. **Google Slides** (`google_slides`): Inspect deck metadata, create presentations via Slides v1 API.
    7. **Google Tasks** (`google_tasks`): List tasklists, list tasks, create tasks via Tasks v1 API.
    8. **Google Contacts** (`google_contacts`): Verified contact lookup via People API.
  - Added roadmap planned service definitions for Microsoft Outlook, OneDrive, Calendar, Slack, Notion, Canva, Dropbox, Trello, Linear, and Discord with clear `planned` status badges.
- **Zero-Mock Official OAuth 2.0 Engine**:
  - Eradicated all synthetic mock codes, tokens, and browser prompt bypasses from production backend and frontend.
  - Implemented official Google OAuth 2.0 authorization code flow with offline refresh tokens (`access_type=offline`, `prompt=consent`), state verification, and PKCE.
  - Added proactive automatic token refresh before API calls when tokens expire within 60 seconds (`IntegrationManager.get_valid_access_token`).
  - Added honest `CONFIGURATION_REQUIRED` status when developer credentials (`CLIENT_ID` / `CLIENT_SECRET`) are not configured, with detailed setup instructions modal.
- **Real Provider API Client (`GoogleApiClient`)**:
  - Built comprehensive REST API client with Bearer authorization, RFC 2822 MIME decoding, base64url parsing, and prompt injection defense.
  - Real health check probes for each service testing live Google endpoints.
- **Expanded Real Tool Catalogue**:
  - Added live Web Research tools: `web_search` (DuckDuckGo live web search with citations) and `web_fetch_page` (live HTTP retrieval with HTML cleaning and SSRF protection).
  - Added Data Analysis tools: `data_read_csv` (CSV inspection in workspace sandbox) and `data_statistics` (numeric column statistics).
  - Added Sandboxed Code Execution: `code_execution_python` (isolated subprocess with 5-second timeout, memory bounds, and stripped environment).
- **Redesigned Integrations View (`IntegrationsView.tsx`)**:
  - Category filtering (All, Google Workspace, Developer Tools, Communication, Productivity, Storage, Design & Media).
  - Live search input filtering services by name and capabilities.
  - Independent service cards with real status badges, account email display, capabilities checklist, Details modal, and Configure modal.
  - Listens for OAuth popup `postMessage` callback for seamless authorization without full-page reloads.
- **Documentation**:
  - Created `docs/integrations/GOOGLE_SETUP.md` with complete step-by-step Google Cloud console setup instructions.
  - Created `docs/integrations/GITHUB_SETUP.md` with GitHub OAuth application configuration guide.
  - Created `docs/integrations/PROVIDER_MATRIX.md` with technical scope and capability matrix across all providers.
  - Authored functionality audit report in brain artifacts.
- **Verification**:
  - 129 backend tests passing (100% pass rate).
  - 0 TypeScript compilation errors; Vite production bundle built in 1.99s.
  - Full Playwright browser MCP verification of the independent service cards, configuration modal, and category filtering.

### Added
- **Persistent Automation System**:
  - Alembic migration `008_automations_and_integrations.py` adding `automations`, `automation_executions`, `integration_connections`, `integration_sync_logs`, `notifications`, and `briefings` tables.
  - SQLAlchemy models in `backend/app/models/automation.py`.
  - Comprehensive schemas supporting `one_time`, `interval`, `daily`, `weekly`, `monthly`, `cron`, and `manual` trigger types in `backend/app/automations/schemas.py`.
  - Timezone-aware next run calculation handling DST with `zoneinfo` and `croniter` in `backend/app/automations/scheduler_utils.py`.
- **Background Execution & Scheduling Engine**:
  - Celery Beat periodic schedule configured (`dispatch-due-automations-every-minute`) in `backend/app/tasks/celery_app.py`.
  - Reliable task executor (`AutomationExecutor`) with step-by-step tool dispatch, duration tracking, idempotency enforcement, and retry policies.
  - Resilient local asynchronous fallback in `AutomationService.trigger_run` ensuring zero dropped tasks when Celery workers or Redis are offline.
- **Natural-Language Automation Creator**:
  - `AutomationInstructionParser` converting natural descriptions (e.g. "Every morning at 8 AM, prepare a briefing...") into structured validated configurations.
  - Strict tool validation against `ToolRegistry` preventing execution of hallucinated or unregistered tools.
- **Permission & Approval Gating for Automations**:
  - Existing `ToolPermissionEngine` and `ApprovalManager` boundaries strictly enforced on every automation action step.
  - Sensitive (Level 2) and Critical (Level 3) actions halt automation execution with state `WAITING_FOR_APPROVAL` and generate single-use execution-linked approval requests.
- **First-Party OAuth Integrations Framework**:
  - `BaseIntegrationProvider` interface and `IntegrationManager` with Fernet AES-256 symmetric credential encryption.
  - Google Workspace provider (Gmail, Google Calendar, Google Drive) with 7 native tools.
  - GitHub provider (Repositories, Issues) with 3 native tools.
  - Untrusted external content sanitization (`sanitize_untrusted_text`) escaping XML tags and delimiter breakouts (`</tool_output>`).
- **Morning Briefing Generator & Notification Center**:
  - `BriefingService` synthesizing multi-source morning digest from calendar, unread emails, pending approvals, and active automations.
  - Persistent `Notification` system with unread count badge, real-time polling, and dismissal actions.
- **Frontend Dashboards & UI Widgets**:
  - `AutomationsView.tsx`: Full automations dashboard with metric cards, natural language creation modal with live preview, enable/disable toggle, manual run button, and execution history drawer.
  - `IntegrationsView.tsx`: First-party OAuth connection hub for Google Workspace and GitHub with status badges, test probe, and sync actions.
  - `NotificationBell.tsx`: Interactive notification popover in navigation header.
  - `DashboardOverview.tsx`: Proactive Morning Briefing card with on-demand generation and active automations widget.
- **Testing & Quality Assurance**:
  - Automated test suite expanded to **128 passing backend pytest tests** (100% pass rate).
  - Clean production build (`npm run build`) in 567ms with 0 TypeScript errors.
  - Complete Playwright MCP browser verification across all 10 end-to-end workflows.

---

## [0.5.1] - 2026-11-22 - Phase 3.1: Tool Execution Security Hardening & Real MCP Validation

### Added
- **Single-Use Approval Enforcement & Replay Defense**:
  - Added `is_executed`, `executed_at`, and `requested_by` columns to `tool_approvals` table via Alembic migration `007_approval_security_hardening.py`.
  - Implemented atomic execution claiming via `ApprovalManager.mark_approval_executed`.
  - Approvals cannot be executed more than once; concurrent execution attempts are safely rejected.
- **Explicit Critical Action Confirmation Gate**:
  - `ApprovalDecisionRequest` now requires `confirm_critical: bool = True` for Level 3 Critical actions (e.g. `file_deleter`), preventing accidental approval of destructive tasks.
- **User Ownership & Authorization Enforcement**:
  - Verified user identity in `approve`, `reject`, and `cancel`, preventing cross-user approval tampering (`SecurityException`).
- **Filesystem Sandbox Hardening**:
  - Added null-byte injection rejection and symlink detection in `_validate_safe_path`.
  - Blocked directory hierarchy traversal across `.git`, `.ssh`, `.env`, `.aws`, `.azure`, `node_modules`, `.venv`.
  - Enforced 5MB read limit (`MAX_FILE_READ_BYTES`) and 5MB write limit (`MAX_FILE_WRITE_BYTES`) to prevent memory exhaustion / DoS attacks.
  - Protected root workspace directory and infrastructure files (`.gitkeep`, `.gitignore`) from unauthorized deletion.
- **MCP Prompt Injection & Output Isolation**:
  - `PromptInjectionGuard` enforces a 50KB payload limit (`MAX_OUTPUT_CHARS`) with truncation notices.
  - Delimiter breakout defense: escapes `</tool_output>` inside output to prevent XML container escape.
  - Sanitizes `<script>`, `<iframe>`, `javascript:`, `onerror=`, and system instruction override attempts.
  - Structural isolation verified: `ToolPermissionEngine` evaluates permissions strictly via database rows, rejecting fake approval confirmations from tool outputs.
- **Real Local MCP Server Integration Test Suite**:
  - Created controlled real MCP test server (`backend/tests/mcp_test_server.py`) communicating over JSON-RPC stdio.
  - Added `McpClient.initialize()` protocol handshake.
  - Verified discovery, schema validation, tool registration, execution, timeout handling, connection failures, and malformed responses.
- **Automated Security & Reliability Test Suite**:
  - Added `backend/tests/test_phase3_security_and_reliability.py` with 29 comprehensive security and reliability tests covering approval replay, argument tampering, expiry, cancellation, concurrency races, path traversal, symlink escapes, large files, real MCP, prompt injection, and idempotency.
  - Backend test suite expanded to **119 passing tests** (100% pass rate).

---

## [0.5.0] - 2026-11-22 - Phase 3: Tool Execution & Human-in-the-Loop Approvals

### Added
- **Centralized Tool Execution Engine**:
  - Implemented `ToolExecutionEngine` (`backend/app/tools/engine.py`) orchestrating schema validation, permission checks, approval gating, per-tool timeouts (`asyncio.wait_for`), result normalization, and execution audit logging.
  - Implemented `ToolRegistry` and extended `BaseTool` (`backend/app/tools/base.py`) supporting tool indexing, enabling/disabling, permission classifications, and LLM JSON schemas.
- **Three-Tier Permission Architecture**:
  - Implemented `ToolPermissionEngine` (`backend/app/tools/permissions.py`) classifying actions into Level 1 (Safe - auto-execute), Level 2 (Sensitive - user approval required), and Level 3 (Critical - explicit confirmation required).
- **Human-in-the-Loop Approval Manager (`ApprovalManager`)**:
  - Implemented `ApprovalManager` (`backend/app/tools/approval_manager.py`) providing atomic, race-safe transitions (`pending` -> `approved` / `rejected` / `cancelled`).
  - Cryptographic argument tamper-resistance using canonical SHA-256 argument hashing (`CanonicalArgumentHasher` in `validator.py`).
  - Approval expiration handling and auto-invalidation upon argument tampering.
- **Model Context Protocol (MCP) Integration**:
  - Implemented `McpClient` and `McpServerManager` (`backend/app/tools/mcp.py`) supporting stdio / HTTP JSON-RPC MCP servers, tool discovery, schema registration, and server health tracking.
  - Implemented `PromptInjectionGuard` isolating tool outputs in `<tool_output>` blocks and sanitizing adversarial injection tokens (`<system>`, `ignore previous instructions`).
- **Native Built-in Sandboxed Tools**:
  - Registered 8 native tools in `backend/app/tools/builtin.py`: `get_system_time`, `calculate`, `text_processor`, `json_validator`, `file_reader`, `file_searcher`, `file_writer` (Sensitive), and `file_deleter` (Critical).
  - Path-traversal sandbox protection: all file tools resolve paths strictly against `WORKSPACE_STORAGE_DIR`, rejecting directory escapes (`..`) and blocking sensitive files (`.env`, `id_rsa`).
- **Database Schema Migration**:
  - Alembic migration `006_tool_execution_and_approvals.py` creating `tool_approvals`, `tool_executions`, and `mcp_servers` tables.
- **REST APIs**:
  - Added `/api/v1/tools` endpoints (catalog listing, tool detail, direct execution, execution history, MCP server management).
  - Added `/api/v1/approvals` endpoints (listing with status filtering, approval details, approve, reject, cancel).
- **Conversational Multi-Round Tool Calling**:
  - Updated `stream_chat` in `backend/app/conversations/service.py` to support tool calling in chat SSE streams, live approval card triggering, buffer reset, and multi-round explanation synthesis (up to 5 rounds).
- **Frontend Dashboards & In-Chat Approvals**:
  - `ApprovalsView.tsx`: Approvals dashboard with metrics cards, status tabs (All, Pending, Approved, Rejected, Expired, Cancelled), argument modal, and confirmation dialogs.
  - `ToolsView.tsx`: Tools hub with registered catalog, JSON schema inspector, test execution runner, and MCP server configuration manager.
  - `ActivityLogsView.tsx`: Execution audit log with status badges, timestamps, durations, and details modal.
  - `ChatMessage.tsx`: In-chat interactive Approval Card with direct Approve & Execute and Reject actions.
- **Automated Test Suite**:
  - Added `backend/tests/test_phase3_tools_and_approvals.py` with 19 automated tests covering registration, schema validation, canonical hashing, secret redaction, safe execution, sensitive approval creation, atomic transitions, argument tamper invalidation, expiration, path-traversal sandbox defense, prompt injection defense, and REST APIs.
  - Total test suite expanded to **90 passing tests** (100% pass rate).

---

## [0.4.6] - 2026-11-22 - Advanced Conversational Intelligence, System Prompt & Assistant Harness

### Added
- **Centralized Context Management Service (`ContextBuilder`)**:
  - Implemented `ContextBuilder` (`backend/app/conversations/context_builder.py`) unifying prompt construction, untrusted background context delimitation, behavioral guardrails, and sliding-window token budgeting into a single dedicated service.
  - Replaced scattered string concatenations with structured, partitioned prompt sections:
    1. Core Identity & Role (intelligent, capable, conversational personal AI; not a database query interface).
    2. Anti-Robotic Conversational Directives:
       - Strict prohibition on meta-retrieval announcements: eliminates phrases like "Based on your stored data...", "According to your saved memories...", "Based on information in your database...".
       - Seamless fact weaving: incorporates known user context directly as established common ground.
       - Transparent memory reporting: when explicitly asked ("What do you remember about me?", "Where did you get that information?"), answers completely, accurately, and honestly.
       - No repetitive filler openings: eliminates "Sure!", "Certainly!", "Of course!", "Great question!".
       - No repetitive boilerplate closures: eliminates "Let me know if you need anything else".
       - Natural follow-up and pronoun resolution: understands "What about that?", "Explain the second one", "its disadvantages" from conversation history.
       - Direct answers: concise answers for simple queries ("2 + 2" -> "4").
       - Uncertainty handling: acknowledges lack of information instead of inventing facts.
    3. General Knowledge Independence:
       - Authoritative answers on general knowledge topics (operating systems, binary search, science, math) without requiring or fabricating personal user memories.
    4. Response Formatting Engine:
       - Integrated GFM table matrices, checklists, and code-only zero-fluff rules.
    5. Untrusted Data Safeguards:
       - Delimits `<retrieved_context>` with strict warnings that memories are untrusted past interaction facts, not executable system instructions.
- **Configurable Assistant Personality & Communication Style**:
  - Implemented `AssistantPersonalityConfig` and `PersonalityService` (`backend/app/conversations/personality.py`) stored in PostgreSQL `system_metadata`.
  - Configurable parameters: assistant name, communication style (natural, concise, technical, detailed), formality (balanced, casual, formal), detail level (balanced, concise, in-depth), memory usage mode (natural_weave, minimal, explicit), emoji usage (minimal, none, expressive), and custom behavioral guidelines.
  - Added REST endpoints: `GET /api/v1/conversations/settings/personality` and `PUT /api/v1/conversations/settings/personality`.
  - Added interactive "Assistant Identity & Conversational Personality" settings card in `frontend/src/pages/SettingsView.tsx` with live update feedback.
- **Token Budgeting & Sliding Window History**:
  - `ContextBuilder.build_chat_messages` enforces token budgets (default 6000 tokens), preserving opening context and recent conversation turns while pruning intermediate messages during long chats.
- **Enhanced Memory Delimitation (`retrieve_relevant_memory_context`)**:
  - Delimited `<retrieved_context>` with dual-layer anti-robotic instructions, preventing models from echoing database retrieval phrases.
- **Automated Behavioral Test Suite**:
  - Added `backend/tests/test_assistant_intelligence.py` with 14 automated tests covering all 10 behavioral prompt scenarios (general knowledge independence, seamless memory weaving, project context, irrelevant memory rejection, follow-up pronoun resolution, explicit memory transparency, conflicting memory, table formatting, direct 2+2 answer, uncertainty handling, prompt structure, personality directives, API CRUD, and token budgeting).
  - Backend test suite expanded to **71 passing tests** (100% pass rate).
  - Frontend production build verified with 0 errors.

---

## [0.4.5] - 2026-11-22 - Advanced Response Formatting & Voice Conversation System

### Added
- **Intelligent Response Formatting Pipeline**:
  - Implemented automatic format detection and strict instruction compliance in `DEFAULT_SYSTEM_INSTRUCTION` (`backend/app/conversations/service.py`).
  - Supports natural language requests for GitHub Flavored Markdown (GFM) tables, comparison matrices, numbered lists, bullet points, checklists (`- [ ]`), step-by-step tutorials, interview-ready answers, and Mermaid diagrams.
  - Zero-fluff rule: when user asks for "only JSON" or "only code", conversational preamble and postamble commentary are strictly avoided.
  - Responsive GFM Table rendering in React: styled table headers, zebra striping, subtle borders, `overflow-x-auto` horizontal scrolling container, and resilient rendering during SSE streaming without flicker.
- **Message Action Bar**:
  - Added Copy Message text with temporary green checkmark feedback.
  - Added Copy Code block button on code snippets.
  - Added Read Aloud / Play Audio toggle with pulsing active speaker animation.
  - Added Stop Audio control.
  - Added Regenerate Response button triggering prompt resubmission.
- **Complete Voice Input System (Speech-to-Text)**:
  - Added microphone button to `ChatInput` with interactive recording state UI.
  - Live recording duration counter (`00:05`), pulsing red indicator, Cancel button, and Done/Finish button.
  - Records audio via browser `MediaRecorder` API into `audio/webm` and uploads to `POST /api/v1/voice/transcribe`.
  - Populates transcribed text directly into the chat input textarea for user review and editing before sending.
  - Graceful handling of browser microphone permission denial and unsupported browser APIs.
- **Complete Voice Output System (Text-to-Speech)**:
  - Play / Read Aloud button on completed assistant responses.
  - Client-side zero-cost speech synthesis using Web Speech API (`window.speechSynthesis`).
  - Implemented `VoiceService.clean_markdown_for_speech` (`backend/app/voice/service.py`) converting markdown tables into natural spoken sentences, skipping code blocks gracefully, converting checklists, and stripping markdown syntax.
  - Added backend route `POST /api/v1/voice/clean-for-speech` with robust testing.
  - Added Voice Settings modal: toggle voice enabled/disabled, auto-play response toggle, voice selector dropdown, and speed slider (0.5x to 2.0x).
  - Preference persistence in PostgreSQL `system_metadata` table via `GET` / `PUT` `/api/v1/voice/preferences`.
- **Automated Verification**:
  - Added `backend/tests/test_voice.py` covering table speech cleaning, code block speech cleaning, JSON speech cleaning, checklists, audio upload validation, and voice preferences CRUD.
  - Total automated backend tests increased to **57 passing tests** (100% pass rate).
  - Clean TypeScript compilation and Vite production build (0 errors).

---

## [0.4.4] - 2026-11-22 - Phase 2 ChatGPT-Style Intelligent Personal Memory System

### Added
- **Intelligent Structured Memory Schema & Database Migration**:
  - Added Alembic migration `005_intelligent_memory_attributes.py` (`005_intelligent_memory_attrs`) introducing 6 new fields:
    - `subcategory` (varchar 64) for granular ontology tags (`current_location`, `friend`, `degree`, `technical_decision`).
    - `temporal_scope` (varchar 32) tracking temporal validity (`current`, `permanent`, `temporary`, `previous`).
    - `valid_from` & `valid_until` (timestamptz) for chronological lifecycle auditing.
    - `is_current` (boolean, indexed) allowing instant filtering of active current facts versus superseded historical records.
    - `original_statement` (text) recording raw verbatim user utterances for auditability and verification.
  - Added indexes on `subcategory`, `temporal_scope`, and `is_current`.
  - Updated `Memory` model, Pydantic schemas, and `MemoryRepository` with full support for temporal scope and current state filters.
- **Location Intelligence & Seamless Relocation Transitions**:
  - Differentiates current temporary location ("I am in Kasiriganapalli") from permanent residence ("I live in Kasiriganapalli") and hometown ("My hometown is Kasiriganapalli").
  - Seamless location transition: when a relocation event occurs ("Actually I moved to Bangalore"), existing current location records are automatically marked `temporal_scope = "previous"`, `is_current = False`, and archived with transition audit history (`metadata_json.history`), while the new location is recorded as `temporal_scope = "current"`, `is_current = True`.
- **Multi-Fact Clause Segmentation in Natural Language**:
  - Implemented `split_into_clauses` resolving compound sentences with shared subjects (e.g., "I am studying B.Tech IT and building a Flutter app" cleanly extracts both the educational degree and active project independently).
  - Robust handling of academic degrees and abbreviations containing periods (e.g. `B.Tech`, `M.Sc`).
- **Dual Extraction Strategy (LLM Provider + Heuristic Fallback)**:
  - Implemented `extract_via_llm` querying the active configured LLM provider for structured JSON memory candidate extraction when online.
  - Graceful, zero-crash fallback to the comprehensive heuristic extractor when offline, unconfigured, or when credentials are unavailable, populating `extraction_strategy: "llm" | "heuristic"` in the execution trace.
- **Enhanced Spatial & Query Semantic Retrieval**:
  - Updated `LocalSemanticEmbeddingProvider` with domain semantic anchor projections for location and temporal terms.
  - Natural spatial queries ("Where am I currently?", "Which place did I mention?", "Where is the user?") achieve high cosine similarity (>0.35) and reliably retrieve location records.
- **Memory Explorer UI Transparency**:
  - Updated `frontend/src/types/memory.ts` and `frontend/src/pages/MemoryView.tsx` with badges for `subcategory`, `temporal_scope` (emerald for current, amber for previous), `is_current`, and verbatim `original_statement`.

### Fixed
- **Relationship Correction & Targeting**:
  - Fixed relationship correction pattern matching (`Actually, my friend's name is Saranya, not Sarguna`) so the targeted friend's previous record is superseded in-place with history auditing rather than creating duplicate entries.
- **Question Rejection Filter**:
  - Ensured informational queries (e.g., "What is a python decorator?") are strictly rejected from becoming personal memories with clear rejection rationale recorded in trace telemetry.

---

## [0.4.3] - 2026-11-22 - Phase 2 Semantic Memory Extraction & Personal Fact Recognition Overhaul

### Fixed
- **Root Cause of Personal Fact Rejection ("my friend name is sarguna")**:
  - Identified that `extract_heuristic_candidates` was strictly restricted to 5 narrow patterns (`preferences`, `profile`, `projects`, `goals`, `technical_knowledge`), completely lacking extractors for relationships, personal facts, education, career goals, decisions, and casual grammar (such as omitting possessive `'s`).
  - Added comprehensive grammar-tolerant heuristic extractors for 12 categories: `personal_facts`, `relationships`, `education`, `career_goals`, `technical_skills`, `preferences`, `projects`, `important_events`, `decisions`, `ongoing_activities`, `communication_preferences`, and `relevant_context`.
  - Normalizes statements idiomatically into third-person factual assertions (e.g. "my friend name is sarguna" -> "The user's friend is named Sarguna.", "my brother studies mechanical engineering" -> "The user's brother studies mechanical engineering.").
- **Relationship Entity Disambiguation**:
  - Fixed relationship deduplication logic in `reconcile_and_store_memory_with_detail`: verified that distinct people sharing the same relationship (e.g., friend Sarguna vs friend Rahul) are preserved as separate active memories and not overwritten.
  - Added support for relationship enrichment (e.g., "Sarguna is my college friend" enriches "The user's friend is named Sarguna" into "The user's friend Sarguna is a college friend").
  - Added support for explicit corrections (e.g., "Actually, my friend's name is Saranya, not Sarguna" supersedes the target memory and records the previous fact in `metadata_json.history`).
- **Semantic Retrieval Precision**:
  - Enhanced `LocalSemanticEmbeddingProvider` stem normalizations (`named` -> `name`, `studies` -> `study`, etc.) and sign-balanced character n-grams.
  - Adjusted default `MEMORY_SIMILARITY_THRESHOLD` to `0.20`, allowing natural queries ("Who is Sarguna?", "What is my friend's name?", "Do you remember my friend?") to reliably retrieve relevant memories.
- **Question & Hypothetical Rejection**:
  - Added pre-filtering to prevent saving questions ("What is the capital of France?", "What is the weather today?"), commands ("Explain Python loops"), and hypothetical scenarios ("If I had a friend named Bob...").

---

## [0.4.2] - 2026-11-22 - Phase 2 Background Worker Investigation, Task Monitoring & Memory Extraction Transparency Overhaul

### Fixed
- **Root Cause of Queued Tasks**:
  - Identified that Redis broker container was healthy and receiving tasks via `.delay()`, but no Celery worker was running in the environment to consume them.
  - Resolved `TaskService._dispatch_to_worker` limitation where local async fallback was only triggered if Redis connection threw an exception. Added `is_celery_worker_online()` inspect ping: when Celery workers are offline, tasks automatically execute via high-performance in-process `_execute_local_fallback` instead of lingering in `queued`.
  - Fixed `celery_task_id` persistence by awaiting asynchronous assignment instead of fire-and-forget task loops.
  - Swept and drained all 24+ accumulated legacy queued tasks through local async execution (post-sweep: 60 succeeded, 0 queued).
- **Failed Task Investigation**:
  - Confirmed the failed tasks were generated exclusively by pytest tests (`test_task_error_sanitization`) testing multi-line traceback stripping. Verified no unhandled production failures exist.
  - Enhanced error handling with sanitized clean summary messages, retry tracking (0/3), and exponential backoff configuration.

### Added
- **Full Memory Extraction Pipeline Transparency**:
  - Implemented `extract_and_reconcile_memories_with_trace` (`backend/app/memory/extraction.py`) recording all 9 pipeline stages:
    1. Source conversation identified
    2. Relevant messages collected
    3. Candidate memories extracted
    4. Sensitive information filtering performed
    5. Candidate embedding generated
    6. Vector similarity search conducted
    7. Semantic duplicate check evaluated
    8. Candidate merged, created, or superseded
    9. Result saved to database
  - Captured structured extraction categories: `created_memories`, `updated_memories` (with `previous_content` and `action: superseded`), `duplicate_memories` (with similarity score), `filtered_candidates` (with redaction reason), and `rejected_candidates`.
- **Extended Background Task Schema & Telemetry**:
  - Added fields to `BackgroundTaskResponse`: `source_conversation_id`, `source_conversation_title`, `source_message_id`, `execution_mode`, `worker_id`, `queue_wait_ms`.
  - Added `WorkerHealthResponse` schema and `GET /api/v1/tasks/health` endpoint returning real Redis latency, worker ping, registered tasks, active and reserved task counts.
  - Added `POST /api/v1/tasks/sweep-stale` endpoint allowing manual or automated sweeping of tasks queued longer than a specified duration.
  - Added `TaskStatsResponse` metrics: `oldest_queued_wait_seconds`, `average_wait_seconds`, `stale_queued_count`.
- **Task Search, Filter, and Sort**:
  - Enhanced `list_tasks` and `GET /api/v1/tasks` with `search` query parameter, `sort_by` (`created_desc`, `created_asc`, `duration_desc`, `duration_asc`), and task type filtering.
- **Frontend Slide-Over Task Details Drawer & Transparency UI**:
  - Created `TaskDetailsModal` (`frontend/src/components/tasks/TaskDetailsModal.tsx`) with three specialized inspector tabs:
    - *Overview & Source*: lifecycle timing, queue wait time, execution runtime (`Celery Worker` vs `Local Async Fallback`), worker ID, source conversation & message context with automated credential redaction badge.
    - *Memory Extraction*: visual 9-stage pipeline checklist, metric cards, and structured cards for created, superseded, duplicate, and filtered memory candidates.
    - *Input & Raw Results*: formatted JSON inspection with copy-to-clipboard.
  - Overhauled `TasksView` (`frontend/src/pages/TasksView.tsx`):
    - Live **Worker System Health** panel showing Redis broker connection latency, Celery worker online status, and active execution strategy.
    - **Queue Latency** panel with oldest wait time, average wait time, and stale (>5m) count.
    - "Process Stale Tasks" trigger button when unconsumed jobs are detected.
    - Instant search, type filtering, and sorting dropdown.
- **Worker Execution Script**:
  - Added `start_worker.ps1` for starting a local Celery worker on Windows with `--pool=solo`.

---

## [0.4.1] - 2026-11-22 - Bugfix: Model Streaming, DNS Resilience, Active Models & Credential Display

### Fixed
- **OpenRouter Model Availability & 404 Resolution**:
  - Replaced retired free model slugs (`meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`, `deepseek/deepseek-chat:free`, `qwen/qwen-2.5-coder-32b-instruct:free` which OpenRouter deprecated with 404s) with live, verified active models:
    - Primary default free model: `nvidia/nemotron-3.5-lightning:free` (131k context, open reasoning, zero cost).
    - Free Models Router: `openrouter/free` (official dynamic router that automatically routes to high-availability free models).
    - Secondary fallback: `google/gemma-4-31b-it:free`.
  - Added auto-migration in `ModelService.get_or_create_policy` so existing database rows seamlessly upgrade from legacy dead slugs without manual database updates.
- **DNS Lookup Resilience (`[Errno 11001] getaddrinfo failed`)**:
  - Added connection retry loops (2 retries with 0.5s pause) in `OpenRouterProvider.chat_stream`, `chat_complete`, `test_connection`, and `list_models` for transient Winsock/DNS network glitches (`socket.gaierror`, `httpx.ConnectError`, `httpx.NetworkError`).
  - Formatted `[Errno 11001]` and socket errors into human-friendly diagnostic messages advising on network or DNS status instead of raw exception traces.
- **Reasoning Model Stream Support**:
  - Enhanced `chat_complete` and `chat_stream` in `OpenRouterProvider` to handle models that emit reasoning tokens (`choice.message.reasoning` / `choice.delta.reasoning`), preventing empty responses.
- **API Key Persistence Display in Settings UI**:
  - Added a prominent status card in `frontend/src/pages/SettingsView.tsx` displaying `API Key Configured & Active: sk-or-••••••••c3e0` with an encrypted database badge and green checkmark.
  - Clarified that typing into the API key input is only required to replace the existing key; leaving it blank preserves the configured key.
  - Added automatic synchronization of `OPENROUTER_API_KEY` to `backend/.env` upon saving in `ProviderService.save_provider_config` for cross-container and process restart resilience.
- **End-to-End Verification**:
  - All 39 backend tests passing (100% pass rate).
  - Clean TypeScript compilation and Vite production build in 721ms.
  - Verified live streaming chat completion across `nvidia/nemotron-3.5-lightning:free`, `openrouter/free`, and `openai/gpt-4o-mini`.

---

## [0.4.0] - 2026-11-22 - Phase 2 Semantic Memory & Background Workers Complete

### Added
- **pgvector Semantic Memory Store**:
  - `Memory` model (`backend/app/models/memory.py` / `app/memory/models.py`) with 384-dimensional pgvector `Vector` column, importance, confidence, category, timestamps, and JSON metadata.
  - Alembic migration `004_semantic_memory_and_tasks.py` adding `memories` table, HNSW cosine vector index (`vector_cosine_ops`), and `background_tasks` table.
  - CRUD operations and statistics endpoints under `/api/v1/memories`: create, list, retrieve, update, delete, archive/unarchive, stats, and semantic vector search.
- **Provider-Independent Embedding Architecture**:
  - Pluggable `BaseEmbeddingProvider` interface and `EmbeddingRegistry` (`backend/app/memory/embeddings.py`).
  - Default `LocalSemanticEmbeddingProvider` generating 384-dimensional dense vectors using subword and character n-gram projections with L2 unit normalization (zero network downloads, sub-millisecond execution).
  - Pluggable `OpenRouterEmbeddingProvider` for cloud embedding endpoints.
- **Automatic Memory Extraction & Deduplication**:
  - `extract_and_reconcile_memories` pipeline (`backend/app/memory/extraction.py`) extracting durable profile facts, user preferences, goals, and active projects.
  - Strict security regex filter discarding passwords, API keys, Bearer tokens, financial numbers, and trivial chatter.
  - Semantic deduplication (>= 0.85 similarity): updates existing memory, bumps confidence, and preserves historical versions in `metadata_json.history`.
- **Isolated Semantic Retrieval**:
  - `retrieve_relevant_memory_context` (`backend/app/memory/retrieval.py`) querying vector store and ranking matches via multi-factor scoring (`0.6*similarity + 0.25*importance + 0.15*confidence`).
  - Safe `<retrieved_context>` prompt injection separating personal background facts from system instructions.
- **Redis & Celery Background Workers**:
  - Redis container (`redis:7-alpine`) service added to `docker-compose.yml`.
  - Celery application instance (`backend/app/tasks/celery_app.py`) with soft/hard timeouts, retries, and task handlers (`extract_memory_celery_task`, `reindex_embeddings_celery_task`).
  - Resilient local asynchronous fallback in `TaskService` guaranteeing task execution even if Celery/Redis is temporarily offline.
  - Task management endpoints under `/api/v1/tasks`: listing, details, stats, cancellation, and retrying.
- **Frontend Dashboards**:
  - **Memory Explorer** (`frontend/src/pages/MemoryView.tsx`): Overview statistics, category distribution badges, full-text & semantic search, category filter, active vs archived view, Add/Edit Memory modal, and deletion controls.
  - **Tasks Dashboard** (`frontend/src/pages/TasksView.tsx`): Status metrics, live 4s auto-refresh polling, task duration indicators, retry and cancel actions.
  - Activated `Memory` and `Tasks` in navigation sidebar and `App.tsx` router.
- **Automated Tests**:
  - Added 9 new automated tests across `test_memory.py`, `test_memory_intelligence.py`, and `test_tasks.py` (39 total tests passing, 100% pass rate).
  - Verified browser workflows using Playwright MCP for both Memory and Tasks views.

---

## [0.3.0] - 2026-11-22 - Provider-Independent Multi-Model Architecture & Cost Controls

### Added
- **Central Model Registry & Multi-Model Architecture**:
  - `CentralModelRegistry` (`backend/app/providers/model_registry.py`) providing discovery, classification, context limits, pricing category (`free` vs `paid`), and capability tags for 100+ models.
  - Prioritized free models for zero-cost development: `meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`, `deepseek/deepseek-r1:free`, `deepseek/deepseek-chat:free`, `qwen/qwen-2.5-coder-32b-instruct:free`, `mistralai/mistral-7b-instruct:free`.
  - Commercial paid models (`openai/gpt-4o-mini`, `openai/gpt-4o`, `anthropic/claude-3.5-haiku`, `anthropic/claude-3.5-sonnet`) supported as optional capabilities.
  - Endpoints under `/api/v1/models`: `GET /api/v1/models` (catalog listing with free/paid filters), `GET /api/v1/models/policy`, `PUT /api/v1/models/policy`, and `GET /api/v1/models/metrics`.
- **Operational Modes & Strict Free-Only Guardrails**:
  - Three distinct operational modes: `free_only` (default), `paid_enabled`, and `manual`.
  - Strict enforcement: Under `free_only` mode, paid models are guaranteed never to be executed or selected during fallback; attempts are rejected or sanitized to free defaults.
  - Per-request cost ceiling controls (`max_cost_per_request`).
- **Configurable Fallback Chains**:
  - Multi-candidate fallback execution loop in `stream_chat` (`backend/app/conversations/service.py`).
  - Seamless fallback switching on rate limits (429) or provider errors with real-time SSE notice events delivered to client.
  - Mode-based fallback filtering guaranteeing no paid models appear in fallback chain under `free_only` mode.
- **Token Usage, Cost & Performance Telemetry**:
  - `model_execution_metrics` table and Alembic migration `003_model_policy_and_metrics.py`.
  - Detailed telemetry tracking: prompt tokens, completion tokens, total tokens, estimated cost in USD, and latency in milliseconds.
  - Assistant message metadata persistence (`metadata_json`) storing cost, latency, and fallback indicators.
- **Frontend Upgrades**:
  - Enhanced **Settings View** (`frontend/src/pages/SettingsView.tsx`) with Operational Mode selector, Fallback Chain manager, Cost ceiling input, Token Usage & Analytics dashboard, and Central Model Registry explorer.
  - Enhanced **Chat View** (`frontend/src/pages/ChatView.tsx`) with grouped model selector (Free vs Paid), mode pill indicator, fallback notice banner, and message execution telemetry badges (`ChatMessage.tsx`).
  - New `modelService.ts` API client.
- **Automated Tests**:
  - Added 8 new automated tests in `backend/tests/test_model_registry.py` covering model classification, free-only validation, fallback filtering, cost calculation, policy endpoints, metrics, and streaming fallback execution (30 total tests passing).

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
