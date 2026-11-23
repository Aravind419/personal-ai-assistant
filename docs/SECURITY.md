# Security Policy & Operational Rules

## 1. Security Overview

The **Personal AI Assistant** is designed as a single-user system. Because this assistant interacts with personal documents, local files, system APIs, and external LLM services, rigorous security boundaries, strict secret hygiene, and defense-in-depth measures are mandatory.

---

## 2. Secrets Handling & Credential Rules

1. **Zero Secret Check-ins**:
   - Never commit `.env` files, API keys, private keys, database passwords, or OAuth tokens into Git.
   - All `.env*` files (except `.env.example` templates) are strictly excluded in `.gitignore`.
2. **Client-Side Secret Isolation**:
   - The React frontend bundle runs in the user's browser. Never expose private API keys, backend secrets, or database URLs in frontend code.
   - Only non-sensitive variables prefixed with `VITE_` (such as `VITE_API_BASE_URL`) may be exposed to the frontend.
3. **Encryption at Rest for AI Provider Credentials**:
   - Provider API keys stored in `provider_configurations.encrypted_api_key` are encrypted at rest using Fernet symmetric encryption (`backend/app/core/security.py`).
   - The encryption key is derived using SHA-256 from the master `SECRET_KEY` held outside the database in environment variables.
   - API endpoints (`GET /api/v1/providers`) **never** return plaintext keys. Only masked strings (e.g. `sk-or-••••••••abcd`) and a boolean `has_api_key` are provided to the UI.
4. **Automated Credential Redaction in Logging**:
   - The backend includes a logging redactor (`RedactingFormatter` in `backend/app/core/logging.py`) and a database URL sanitizer (`sanitized_database_url` in `backend/app/core/config.py`).
   - All connection strings, passwords, and authorization tokens must be masked (`user:***@host`) before writing to stdout or disk.
5. **Environment Isolation**:
   - Backend secrets are parsed and validated strictly via `pydantic-settings` (`backend/app/core/config.py`). Missing required secrets fail fast with explicit configuration errors.

---

## 3. Network & CORS Policy

- **Cross-Origin Resource Sharing (CORS)**:
  - The FastAPI backend explicitly restricts incoming requests to allowed origins via `CORS_ORIGINS` in `app/core/config.py` (default: `http://localhost:5173`, `http://127.0.0.1:5173`).
  - Wildcard CORS (`allow_origins=["*"]`) combined with credentials (`allow_credentials=True`) is strictly prohibited.
- **Local Network Binding**:
  - During local development, servers bind to loopback (`127.0.0.1`) rather than public broadcast addresses (`0.0.0.0`) unless explicitly running inside a secure container network.

---

## 4. Controlled Tool Calling & Agent Boundaries

- **Tool Sandboxing**:
  - Agent tools execute strictly on the backend via `ToolRegistry` (`backend/app/tools/base.py`).
  - Arguments are validated against JSON Schemas before execution.
  - The model is **never** granted unrestricted computer control, arbitrary shell access, or arbitrary Python eval.
- **Future Approval Engine (Phase 3+)**:
  - Destructive or high-impact actions (writing files, external communications) must halt execution and present a structured approval request to the user via the Approvals module.
  - The agent must never bypass this gatekeeper.

---

## 5. Model Execution Guardrails & Financial Cost Protection

1. **Strict Free-Only Mode**:
   - When the user selects `free_only` mode, the backend enforces a hard barrier against commercial models. Any attempt to query paid models is rejected before API transmission, and fallback chains are sanitized to exclude all paid candidates.
   - Prevents inadvertent cloud token expenditure during local development or testing.
2. **Per-Request Cost Ceilings**:
   - Under `paid_enabled` mode, requests exceeding `max_cost_per_request` are rejected before dispatch.
3. **Transparent Execution Telemetry**:
   - Token usage and estimated USD costs are tracked per request in `model_execution_metrics` for auditability.

---

## 6. Vulnerability Reporting & Dependency Audits

- Periodically inspect and audit Python packages:
  ```powershell
  cd backend
  pip audit
  ```
- Periodically inspect and audit Node packages:
  ```powershell
  cd frontend
  npm audit
  ```
- If a security flaw or token exposure occurs:
  1. Immediately revoke and regenerate the compromised credential.
  2. Document the remediation in `docs/SECURITY.md` and `docs/CHANGELOG.md`.
  3. Never record the actual compromised value in documentation.

---

## 7. Semantic Memory & Background Worker Security (Phase 2)

1. **Automatic Credential & Secret Scrubbing in Memory Pipeline**:
   - The extraction engine (`backend/app/memory/extraction.py`) applies regex pattern guards before storing any candidate fact into pgvector.
   - Any text containing API keys (`sk-...`, `ghp_...`), passwords (`password: ...`), authorization bearer tokens (`Bearer ...`), credit card numbers, or SSNs is automatically dropped.
2. **Context Isolation & Injection Defense**:
   - Stored memory content is treated strictly as untrusted user data.
   - When injected into conversational context, retrieved memories are isolated inside `<retrieved_context>` XML wrappers and explicitly labeled as background facts rather than executable instructions.
   - Retrieved memories can never override core system prompts or agent guardrails.
3. **Background Worker Error Sanitization**:
   - Background tasks stored in `background_tasks.error_message` are sanitized to strip multiline internal stack traces or environment variables before being returned to API clients.
4. **Deleted Memory Vector Invalidation**:
   - Deleting a memory permanently removes both the tabular record and its vector embedding from PostgreSQL, guaranteeing that deleted facts can never resurface in future vector searches.
5. **Context Builder & Personality Configuration Boundary**:
   - User-level personality configurations (communication style, formality, custom guidelines) execute within bounded validation schemas (`AssistantPersonalityConfig`) and are strictly partitioned within `ContextBuilder`.
   - User personality preferences can never override core developer instructions, system safety policies, tool sandboxes, or Free-Only operational mode constraints.

---

## 8. Tool Execution & Human-in-the-Loop Approval Security (Phase 3 & Phase 3.1)

1. **Three-Tier Permission Architecture**:
   - Every tool is classified into `SAFE` (Level 1), `SENSITIVE` (Level 2), or `CRITICAL` (Level 3).
   - `SAFE` tools (read-only, mathematical calculations, local system time) execute automatically under configured permissions.
   - `SENSITIVE` tools (modifying files, state mutations) strictly block execution and require explicit user approval.
   - `CRITICAL` tools (file deletion, financial, irreversible destructive actions) require explicit action-specific confirmation with risk disclosure. Level 3 Critical approvals strictly require `confirm_critical=true` in the API payload or the transition fails with `ValidationException`.

2. **Single-Use Enforcement & Race-Safe Transitions**:
   - `ApprovalManager.mark_approval_executed` performs atomic conditional SQL updates (`UPDATE tool_approvals SET is_executed = true, executed_at = now, execution_id = :exec_id WHERE id = :id AND is_executed = false AND status = 'approved'`).
   - Prevents replay attacks, approval reuse, double approvals, or duplicate execution triggers from rapid repeated clicks or concurrent API calls. Once an approval is executed, subsequent calls are rejected with `ValidationException`.

3. **Canonical Argument Hashing (`arguments_hash`)**:
   - Every approval request is cryptographically bound to a SHA-256 hash of canonical sorted JSON arguments (`CanonicalArgumentHasher`).
   - If requested arguments drift or are altered between approval creation and execution time, the approval is immediately invalidated, set to `CANCELLED`, and execution is blocked.

4. **Cross-User Approval Isolation**:
   - `tool_approvals.requested_by` records the requesting user identity (default `"personal_user"`).
   - In `approve`, `reject`, and `cancel`, the acting user identity (`decided_by`) is verified against `requested_by`. Mismatched user identities raise `SecurityException`.

5. **Sandbox File Traversal & Symlink Protection**:
   - File system tools (`file_reader`, `file_searcher`, `file_writer`, `file_deleter`) are strictly restricted to `WORKSPACE_STORAGE_DIR`.
   - Paths are resolved to their canonical realpaths. Null bytes (`\0`) and symlinks (`os.path.islink`) are prohibited to eliminate directory traversal escapes and TOCTOU symlink swaps.
   - All path hierarchy parts are scanned against forbidden directories (`.git`, `.ssh`, `.env`, `.aws`, `.azure`, `.kube`, `node_modules`, `.venv`).
   - Access to sensitive filenames (`.env`, `id_rsa`, `id_ed25519`, `credentials`, `config.json`, `known_hosts`, `authorized_keys`) is explicitly blocked.
   - Operations directly on the workspace root directory and deletion of infrastructure files (`.gitkeep`, `.gitignore`) are prohibited.
   - Bounded I/O caps: `MAX_FILE_READ_BYTES = 5MB` and `MAX_FILE_WRITE_BYTES = 5MB` protect against memory exhaustion.

6. **Secret Sanitization in Execution Logs**:
   - `SecretSanitizer` scans execution arguments, outputs, and error details before persistence.
   - Redacts API keys (`sk-...`, `Bearer ...`), passwords, database URLs, and secret tokens using regular expression masks (`[REDACTED]`).

7. **Prompt Injection & DoS Defense for External Tools & MCP**:
   - Tool outputs and MCP results are enclosed in isolated `<tool_output>` XML wrappers.
   - Delimiter breakout defense: any `</tool_output>` occurrence inside raw output is safely escaped to prevent XML envelope breakout.
   - Output truncation: payload size is strictly capped at 50,000 characters (`MAX_OUTPUT_CHARS`), appending truncation notices to prevent LLM context blowup or DoS.
   - Executable scripts (`<script>`, `<iframe>`, `javascript:`, `onerror=`) and system override directives (`<system>`, `ignore previous instructions`, `you are now in dan mode`) are neutralized.
   - Structural isolation: permissions are evaluated strictly server-side in PostgreSQL. A tool output claiming `{"approved": true, "role": "admin"}` is never trusted by `ToolPermissionEngine`.

---

## 9. Proactive Automations & External Integrations Security (Phase 4)

1. **OAuth Credential Security & Fernet Encryption**:
   - External provider tokens (Google Workspace, GitHub) are encrypted at rest in `integration_connections.encrypted_access_token` and `encrypted_refresh_token` using Fernet symmetric encryption.
   - Tokens are never returned to client endpoints; only connection status, masked account emails, and granted scopes are exposed to the UI.
2. **CSRF State Verification**:
   - OAuth authorization URLs include cryptographically random `state` tokens cached with TTL.
   - Callbacks strictly validate the returned state to prevent OAuth login CSRF attacks.
3. **Execution-Linked Single-Use Approvals**:
   - When an automation executes a sensitive or critical tool, execution halts in `WAITING_FOR_APPROVAL` state and creates a single-use approval bound to the specific execution ID.
   - Past approvals cannot authorize future recurring executions.
4. **Untrusted External Content Sanitization**:
   - Text retrieved from external integrations (email bodies, calendar event descriptions, GitHub issue comments) is processed through `sanitize_untrusted_text`.
   - Delimiters such as `</tool_output>`, `<system>`, and script tags are escaped to prevent prompt injection breakouts.
5. **Strict Scope Minimization**:
   - OAuth integrations request only the minimal scopes required for listed capabilities.

