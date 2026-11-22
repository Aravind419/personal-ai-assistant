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
