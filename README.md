# 🤖 Local RAG System with Ollama & LangChain

A production-ready Retrieval-Augmented Generation (RAG) system built with **LangChain** and **Ollama** — local by default, with optional per-site cloud LLM support on the Business plan.

## ✨ Features

- 🆓 **Free & Local by Default** - Free/Plus/Enterprise plans run entirely on Ollama, no external API keys needed
- 🏠 **Runs Locally** - Complete privacy and offline operation for Ollama-powered plans
- 🤖 **Bring Your Own LLM** - Business plan sites each configure their own OpenAI, Gemini, or Anthropic key — no shared server credential
- ⚡  **Fast Responses** - Streaming SSE, in-memory question cache, and separate LLM/embed semaphores
- 📎 **Source Citations** - Every answer shows which documents it came from
- 🧠 **Conversation History** - Follow-up questions with context awareness
- 🌐 **Web Interface** - Streamlit-powered chat UI
- 📄 **Multi-Format Support** - PDF, DOCX, Markdown, TXT
- 🔌 **REST API** - FastAPI backend for integrating with external apps
- 🏢 **Multi-Tenant** - Each client gets isolated documents and vector store
- 📤 **Async Document Ingestion** - Upload files and poll for status; text ingestion is synchronous
- 🔑 **API Key Auth** - Per-site access control with hashed keys
- 📊 **Plan & Usage Limits** - Per-site message limits with Free/Plus/Business/Enterprise plans
- 🚦 **Rate Limiting** - 60 requests/minute per API key
- 🐳 **Docker Support** - Full stack with one command

## 🎯 Use Cases

This system is designed to be a **shared AI backend** that multiple independent clients can connect to, each with their own isolated knowledge base:

- **WordPress Multisite** — each sub-site gets its own documents and chatbot
- **SaaS platforms** — embed a knowledgeable chatbot per customer account
- **Agency hosting** — one server powering chatbots for multiple client websites
- **Internal tools** — different teams ingest their own docs and query independently
- **E-commerce** — product/FAQ chatbot per store with isolated product data
- **Documentation sites** — question-answering over technical docs per project

Each tenant is fully isolated — one site can never access another site's data.

## 🛠️ Tech Stack

- **LangChain** - RAG framework
- **Ollama** - Local LLM (Llama 3.2)
- **Qdrant** - Vector database (server mode, Docker)
- **FastAPI** - REST API server
- **SQLAlchemy + SQLite** - Site metadata and request logging
- **slowapi** - Rate limiting
- **Streamlit** - Web chat interface
- **PyPDF** - PDF processing
- **Docker** - Containerization
- **Python 3.10+**

## 📁 Project Structure

```
rag-ollama-project/
├── api.py                   # FastAPI app entry point
├── main.py                  # Core RAG logic (used by Streamlit + CLI)
├── app.py                   # Streamlit web interface
├── routers/
│   ├── status.py            # GET /status
│   ├── ingest.py            # File & text ingestion endpoints + async job queue
│   ├── chat.py              # POST /chat
│   └── admin.py             # Admin site management
├── services/
│   ├── embedding.py         # Ollama embeddings (singleton + batched)
│   ├── vectorstore.py       # Qdrant operations (upsert, query, filter, delete)
│   ├── chunking.py          # Smart chunking: page-aware PDF, heading-aware DOCX, paragraph text
│   ├── retrieval_eval.py    # Retrieval metrics: MRR and Recall@k
│   ├── concurrency.py       # Shared semaphores (embed, llm, upload)
│   ├── cache.py             # In-memory per-site question cache with TTL
│   ├── crypto.py            # Fernet encryption for business plan API keys
│   ├── job_queue.py         # Async upload job queue, status tracking, ETA, retry
│   ├── chat_queue.py        # Async chat job queue for ?async=true mode
│   └── llm.py               # LLM routing (Ollama + per-site external providers)
├── models/
│   └── database.py          # SQLAlchemy models (sites, request_logs)
├── middleware/
│   └── auth.py              # API key + admin auth
├── Dockerfile               # Container image
├── docker-compose.yml       # Ollama + RAG API + Streamlit
├── .dockerignore
├── .env.example
└── requirements.txt
```

## 🚀 Quick Start

<details>
<summary>Click to expand</summary>

### Option A — Docker (Recommended)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) + Docker Compose

```bash
# 1. Clone the repository
git clone https://github.com/timi-ro/rag-ollama-project.git
cd rag-ollama-project

# 2. Configure environment (required — server will not start without ADMIN_SECRET)
cp .env.example .env
# Edit .env and set ADMIN_SECRET to a strong random value:
# python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Start all services
docker compose up -d

# 4. Pull the Ollama model (one-time, ~2GB)
docker exec -it $(docker compose ps -q ollama) ollama pull llama3.2
```

| Service | URL |
|---------|-----|
| Streamlit UI | `http://localhost:8501` |
| RAG API | `http://localhost:8000` |
| API Docs | `http://localhost:8000/docs` |

---

### Option B — Local

**Prerequisites:** [Ollama](https://ollama.com) + Python 3.10+

```bash
git clone https://github.com/timi-ro/rag-ollama-project.git
cd rag-ollama-project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
ollama pull llama3.2
cp .env.example .env
# Edit .env and set ADMIN_SECRET before starting the server
```

```bash
# REST API
uvicorn api:app --reload

# Streamlit UI
streamlit run app.py

# CLI
python main.py
```
</details>

## 🔧 API Reference

<details>
<summary>Click to expand</summary>

Interactive docs with all endpoints, request/response schemas, and a built-in try-it-out tool are available at:

```
http://localhost:8000/docs
```

The following sections cover behaviour that isn't visible in the auto-generated docs.

### Authentication

All `/ingest/*`, `/chat`, and `/usage` endpoints require:
```
X-API-Key: <your-site-api-key>
```

Admin endpoints (`/admin/*`) require:
```
X-Admin-Secret: <your-admin-secret>
```

API keys are shown **only once** when a site is created and are not stored in plaintext. Save the key immediately — there is no way to retrieve it again.

### Plans

| Plan | Message limit | Resets | Storage (chunks) | Approx. storage | LLM |
|------|--------------|--------|-----------------|----------------|-----|
| `free` | 20 (all-time) | Never | 250 | ~3 MB | Ollama |
| `plus` | 2,000 | Every 30 days (rolling) | 10,000 | ~130 MB | Ollama |
| `business` | 5,000 | Every 30 days (rolling) | 50,000 | ~650 MB | Per-site external LLM |
| `enterprise` | Unlimited | — | Unlimited | — | Ollama |

Only successful `/chat` requests (HTTP 200) count toward the message quota. Storage usage and remaining capacity are returned by the `/usage` endpoint under the `storage` key.

Free, Plus, and Enterprise plans use the shared Ollama instance — no external API keys needed. Business plan sites each bring their own credentials (see [Business plan LLM setup](#business-plan-llm-setup) below).

### Business plan LLM setup

Business plan sites use an external LLM provider. Each site configures its **own** API key — there is no shared server-side credential.

**Step 1 — Create or upgrade the site to business:**
```http
POST /admin/sites
X-Admin-Secret: <secret>

{ "name": "my-site", "plan": "business" }
```

**Step 2 — Set the site's LLM credentials:**
```http
PATCH /admin/sites/{id}/llm
X-Admin-Secret: <secret>

{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "api_key": "sk-..."
}
```

Valid providers and their default models:

| Provider | `provider` value | Default model |
|----------|-----------------|---------------|
| OpenAI | `openai` | `gpt-4o-mini` |
| Google Gemini | `gemini` | `gemini-2.0-flash` |
| Anthropic | `anthropic` | `claude-3-5-haiku-20241022` |

`model` is optional — omit it to use the provider default. The API key is stored per-site in the database.

---

### Chat modes

`POST /chat` supports three modes via query parameters:

| Mode | Query param | Behaviour |
|------|------------|-----------|
| Sync (default) | *(none)* | Waits for the full answer, returns JSON |
| Streaming | `?stream=true` | Returns SSE stream — tokens appear as they're generated |
| Async | `?async=true` | Returns 202 with `job_id`; poll `GET /chat/status/{job_id}` |

Retrieval can be scoped with additional query params on all sync and streaming requests:

| Param | Example | Effect |
|-------|---------|--------|
| `doc_id` | `?doc_id=report.pdf` | Only retrieve chunks from this document |
| `file_type` | `?file_type=pdf` | Only retrieve chunks of this file type (`pdf`, `docx`, `text`, `md`) |

**Streaming response format (SSE):**
```
data: {"token": "The "}
data: {"token": "answer "}
data: {"token": "is..."}
data: {"done": true, "sources": ["doc-1"]}
```

Cache hit (identical question asked recently by the same site):
```
data: {"answer": "...", "sources": [...], "done": true, "from_cache": true}
```

The in-memory question cache has a 5-minute TTL by default (`CHAT_CACHE_TTL`). Cached responses return instantly without touching the LLM.

---

### File upload — async job queue

File uploads (`POST /ingest/file`) are processed asynchronously. The endpoint returns `202 Accepted` immediately so clients are never left waiting during long embedding jobs.

**1. Upload a file**
```http
POST /ingest/file
X-API-Key: <key>
Content-Type: multipart/form-data

file=@report.pdf
```
```json
{
  "job_id": "j_a3f9b2c1d4e5",
  "status": "queued",
  "filename": "report.pdf",
  "queue_position": 3,
  "eta_seconds": 90,
  "poll_url": "/ingest/status/j_a3f9b2c1d4e5"
}
```

**2. Poll for status**
```http
GET /ingest/status/j_a3f9b2c1d4e5
X-API-Key: <key>
```
```json
{
  "job_id": "j_a3f9b2c1d4e5",
  "status": "done",
  "filename": "report.pdf",
  "queue_position": 0,
  "eta_seconds": null,
  "created_at": 1741435200.0,
  "started_at": 1741435210.0,
  "completed_at": 1741435245.0,
  "result": { "ingested": 42, "doc_id": "report.pdf" },
  "error": null
}
```

**Job status values:**

| Status | Meaning |
|--------|---------|
| `queued` | Waiting in queue — `queue_position` and `eta_seconds` are set |
| `processing` | Currently being embedded and stored |
| `done` | Successfully ingested — see `result` |
| `failed` | Something went wrong — see `error`. The job can be retried. |

**3. Retry a failed job** (no need to re-upload the file)
```http
POST /ingest/retry/j_a3f9b2c1d4e5
X-API-Key: <key>
```
Returns the same 202 shape as the original upload with the new queue position and ETA.

`eta_seconds` is estimated from a rolling average of the last 20 completed jobs multiplied by `queue_position`. It is `null` until at least one job has completed.

---

### Admin endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/admin/sites` | Create site, returns API key once |
| `GET` | `/admin/sites` | List all sites |
| `PATCH` | `/admin/sites/{id}` | Update plan and/or active status |
| `PATCH` | `/admin/sites/{id}/llm` | Configure external LLM for a business-plan site |
| `POST` | `/admin/sites/{id}/reset` | Clear message logs and/or all documents |
| `POST` | `/admin/sites/{id}/regenerate-key` | Issue a new API key, invalidates the old one |

**Update site** — all fields optional, send only what you want to change:
```http
PATCH /admin/sites/{id}
X-Admin-Secret: <secret>

{ "plan": "plus", "is_active": true }
```

**Reset usage** — both flags default to `false`, opt in explicitly:
```http
POST /admin/sites/{id}/reset
X-Admin-Secret: <secret>

{ "messages": true, "files": true }
```
```json
{ "site_id": 3, "cleared": ["messages", "files"] }
```

| Flag | What gets deleted |
|------|-------------------|
| `messages` | All request logs → message quota resets to zero |
| `files` | All vector chunks → storage quota resets to zero |

**Regenerate API key:**
```http
POST /admin/sites/{id}/regenerate-key
X-Admin-Secret: <secret>
```
```json
{ "site_id": 3, "api_key": "new-key-shown-once" }
```
The previous key stops working immediately. Save the new key — it cannot be retrieved again.

---

### /status response

```json
{
  "status": "ok",
  "version": "1.0.0",
  "ollama": { "model": "llama3.2" }
}
```

### Rate limiting

60 requests/minute keyed on the `X-API-Key` header. Falls back to client IP if no key is present.

### Error responses

| Status | Body | Trigger |
|--------|------|---------|
| `401` | `{"error": "INVALID_API_KEY"}` | Missing or wrong `X-API-Key` |
| `401` | `{"error": "INVALID_ADMIN_SECRET"}` | Missing or wrong `X-Admin-Secret` |
| `429` | `{"error": "RATE_LIMIT_EXCEEDED"}` | Rate limit hit |
| `429` | `{"error": "PLAN_LIMIT_REACHED", "plan": "...", "used": N, "limit": N}` | Message quota exhausted |
| `413` | `{"error": "STORAGE_LIMIT_REACHED", "chunk_limit": N, "chunks_used": N, "chunks_available": N}` | Storage quota exhausted |

</details>

## ⚙️ Environment Variables

<details>
<summary>Click to expand</summary>

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Model used for all Ollama-powered plans (free, plus, enterprise) |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `EMBED_DIM` | `3072` | Embedding dimension — must match the Ollama model (llama3.2 = 3072) |
| `SQLITE_DB_PATH` | `./sites.db` | SQLite database path |
| `ADMIN_SECRET` | **required** | Secret for admin endpoints. The server refuses to start if unset or set to the placeholder value. Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ALLOWED_ORIGINS` | *(none)* | Comma-separated list of allowed CORS origins, e.g. `https://app.example.com`. Leave empty to block all cross-origin requests. |
| `MAX_UPLOAD_BYTES` | `10485760` | Maximum file/text upload size in bytes (default 10 MB) |
| `EMBED_BATCH_SIZE` | `16` | Number of text chunks sent to Ollama per embedding call. Lower values reduce CPU spike; higher values increase throughput. |
| `MAX_INFLIGHT_UPLOADS` | `10` | Maximum number of upload requests actively streaming to disk at the same time. Excess requests queue in memory with negligible overhead. |
| `CHAT_CACHE_TTL` | `300` | Seconds before a cached question expires (default 5 min). Set to `0` to disable caching. |
| `CHAT_CACHE_MAX` | `500` | Maximum number of cached questions per server. Oldest entries are evicted when the limit is reached. |
| `FERNET_KEY` | *(none)* | Fernet encryption key for business plan API keys at rest. Generate with `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. If unset, keys are stored in plaintext (not recommended for production). |

> **Business plan LLM credentials** (OpenAI key, Gemini key, etc.) are stored per-site in the database via `PATCH /admin/sites/{id}/llm` — no server-level environment variables are needed.

</details>

## 📈 Improvements & Curriculum Progress

<details>
<summary>Click to expand</summary>

### Chunking & Retrieval Quality

- [ ] **Page tracking** — Extract text per page in PDF loading and store the page number in each chunk's Qdrant payload.
- [ ] **Section awareness** — Parse `docx` heading styles (`Heading 1`, `Heading 2`) to attach a `section_title` to each paragraph chunk.
- [ ] **Smarter chunking** — Replace character-based chunking with heading-aware and paragraph-boundary strategies to avoid splitting mid-sentence or mid-concept.
- [ ] **Richer payload** — Extend the Qdrant point payload to include `page`, `section_title`, and `file_type`.
- [ ] **Payload filtering** — Use Qdrant's `Filter` with `must` conditions to scope searches to a specific file, file type, or page range.
- [ ] **Retrieval evaluation** — Build a test set of question/answer pairs and measure retrieval precision using MRR and Recall@k metrics.

### Testing

- [ ] **Unit tests for core functions** — `tests/test_chunking.py` covers `chunk_text`, `chunk_pdf`, `chunk_docx`, and `_split_text` (boundary conditions, empty input, section titles, page numbers). Coverage is enforced via `pytest --cov` with a minimum threshold of 40% (currently ~75%).

### Mentor Feedback — Bugs & Quality Fixes

- [ ] **Shared-dict reference** — Replace `[{...}] * n` pattern with a list comprehension so each chunk gets its own metadata dict.
- [ ] **Bare `except Exception`** — Replace with specific exceptions so real errors aren't silently swallowed.
- [ ] **Scoped warning suppression** — Replace global `warnings.filterwarnings("ignore")` with targeted `warnings.catch_warnings()` blocks.
- [ ] **Cross-page chunking for PDFs** — Concatenate full-document text before chunking, while still recording the starting page number per chunk.
- [ ] **Group DOCX paragraphs before chunking** — Collect all paragraphs under a heading section into one block before chunking, so short paragraphs get merged.
- [x] **Duplicate detection on ingest** — Query Qdrant for existing points with the same source filename before upserting to prevent doubled results on re-ingest.

</details>

## 🐛 Troubleshooting

<details>
<summary>Click to expand</summary>

### Ollama not running
```bash
ollama serve
```

### Model not found
```bash
ollama pull llama3.2
```

### Slow first request
First request per site builds the vector index — subsequent requests are fast.

### Chatbot is very slow on macOS (Docker)
Docker on macOS runs inside a Linux VM which has no access to Apple Silicon's Metal GPU. This means Ollama inside Docker falls back to CPU-only inference, making responses 5–10× slower than they should be.

**Fix:** Run Ollama natively on your Mac instead of inside Docker, and point the containers at it:

```bash
# Install and start Ollama natively
brew install ollama
ollama serve
ollama pull llama3.2
```

Then update `OLLAMA_BASE_URL` in `docker-compose.yml` to use the host:
```yaml
OLLAMA_BASE_URL: http://host.docker.internal:11434
```

And remove the `ollama` service from `docker-compose.yml`. Ollama running natively uses Metal GPU acceleration and is dramatically faster.

</details>

## 👩🏼‍💻Author

**Fatima R.**
- Backend Developer | AI Enthusiast
- LinkedIn: [linkedin.com/in/frostami](https://www.linkedin.com/in/frostami/)

---

⭐ Star this repo if you find it useful!

If this project saved you time or helped you build something cool, consider buying me a coffee, it keeps the projects coming!

<p align="center">
  <a href="https://buymeacoffee.com/ForetoldFatima">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="150" alt="Buy Me A Coffee">
  </a>
</p>
