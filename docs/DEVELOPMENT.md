# Development Guide & Troubleshooting

## 1. Prerequisites

Ensure the following tools are installed on your host system:
- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: 3.11+ (Python 3.13 recommended)
- **Node.js**: 20.x or 24.x (Active LTS)
- **Package Managers**: `uv` (recommended) or `pip`, `npm`
- **Docker**: Docker Desktop (for PostgreSQL container)
- **Git**: 2.40+

---

## 2. Initial Setup

### Step 1: Environment Variables
Copy all `.env.example` templates to `.env`:

```powershell
# In project root
Copy-Item .env.example .env

# In backend directory
Copy-Item backend\.env.example backend\.env

# In frontend directory
Copy-Item frontend\.env.example frontend\.env
```

---

### Step 2: Database & Worker Infrastructure (Docker)

Start the PostgreSQL 16 container with `pgvector` and the Redis 7 container:

```powershell
# Start postgres and redis in detached mode
docker compose up -d postgres redis

# Check status
docker compose ps
```

To run a Celery worker locally (optional during development as backend includes automatic async fallback):
```powershell
cd backend
.\.venv\Scripts\celery -A app.tasks.celery_app.celery_app worker --loglevel=info -P solo
```

To stop the container:
```powershell
docker compose down
```

To wipe database data volume:
```powershell
docker compose down -v
```

---

### Step 3: Backend Setup (FastAPI)

1. Navigate to `backend` and install dependencies:
   ```powershell
   cd backend
   uv venv .venv
   uv pip install -r requirements.txt
   ```

2. Run database migrations (ensure Docker container is up):
   ```powershell
   .\.venv\Scripts\alembic upgrade head
   ```

3. Run the automated test suite:
   ```powershell
   .\.venv\Scripts\pytest
   ```
   Acceptance criteria: 100% passing tests (all 90 core tests across health, config, exceptions, security, conversations, chat stream, tools, memory intelligence, voice, and Phase 3 tool execution & approvals).

---

### Step 4: Tool Execution & Approvals Testing

To verify the Phase 3 Tool Execution & Approval system specifically:
```powershell
cd backend
.\.venv\Scripts\pytest tests/test_phase3_tools_and_approvals.py -v
```

To test path-traversal sandboxing:
- Files are confined to `workspace_storage/` in project root.
- The `FileReaderTool`, `FileWriterTool`, and `FileDeleterTool` enforce strict relative path resolution against this directory and block access to parent paths or sensitive file names (`.env`, `id_rsa`, `.git`).

4. Start the backend development server:
   ```powershell
   .\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

- Interactive OpenAPI Swagger Docs: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- Health Check: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- AI Providers: [http://127.0.0.1:8000/api/v1/providers](http://127.0.0.1:8000/api/v1/providers)
- Conversations: [http://127.0.0.1:8000/api/v1/conversations](http://127.0.0.1:8000/api/v1/conversations)

---

### Step 4: Frontend Setup (React + Vite)

1. Navigate to `frontend` and install dependencies:
   ```powershell
   cd frontend
   npm install
   ```

2. Verify TypeScript types and production build:
   ```powershell
   npm run build
   ```

3. Start the Vite development server:
   ```powershell
   npm run dev
   ```

Open your browser at **[http://localhost:5173](http://localhost:5173)**.

---

## 3. Configuring OpenRouter API Key

1. Open the web app at [http://localhost:5173](http://localhost:5173).
2. Click **Settings** in the left sidebar menu.
3. In the **OpenRouter** card, enter your OpenRouter API key (`sk-or-v1-...`).
4. Select your preferred default model (e.g. `OpenAI: GPT-4o Mini` or `Anthropic: Claude 3.5 Haiku`).
5. Click **Test Connection** to verify live credentials and measure network roundtrip latency.
6. Click **Save Configuration**. Your key is securely encrypted at rest via Fernet symmetric encryption and will never be returned in plaintext to the frontend.
7. Navigate to **Chat** to begin chatting with live streaming responses!

Alternatively, you can provide `OPENROUTER_API_KEY=sk-or-v1-...` in `backend/.env` as a local environment fallback.

---

## 4. Running Automated Tests

```powershell
cd backend
.\.venv\Scripts\pytest
```

The test suite runs 39 comprehensive unit and integration tests across:
- `tests/test_config.py`: Environment parsing and sanitization.
- `tests/test_security.py`: Fernet encryption, decryption, and key masking.
- `tests/test_providers.py`: Provider registry, OpenRouter credentials check, and error formatting.
- `tests/test_conversations.py`: Thread creation, listing, retrieval, renaming, and deletion.
- `tests/test_chat_stream.py`: SSE streaming token delivery and message persistence.
- `tests/test_tools.py`: Tool registry and argument validation.
- `tests/test_health.py`: Live database probe and system diagnostics.
- `tests/test_exceptions.py`: Centralized error handlers.
- `tests/test_model_registry.py`: Central model catalog, free-only mode, and fallback chain filtering.
- `tests/test_memory.py`: Semantic memory CRUD, pgvector HNSW search, and statistics.
- `tests/test_memory_intelligence.py`: Secret filtering, memory extraction, conflict resolution, and context injection.
- `tests/test_tasks.py`: Background task lifecycle, status transitions, retries, and error sanitization.
