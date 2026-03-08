# 🤖 Local RAG System with Ollama & LangChain

A production-ready Retrieval-Augmented Generation (RAG) system built with **LangChain** and **Ollama** — local by default, with optional cloud LLM support for the gold plan.

## ✨ Features

- 🆓 **Free & Local by Default** - Free/pro/enterprise plans run entirely on Ollama, no external API keys needed
- 🏠 **Runs Locally** - Complete privacy and offline operation for Ollama-powered plans; gold plan routes to a cloud LLM of your choice
- ⚡ **Fast Responses** - Optimised retrieval pipeline with ChromaDB
- 📎 **Source Citations** - Every answer shows which documents it came from
- 🧠 **Conversation History** - Follow-up questions with context awareness
- 🌐 **Web Interface** - Streamlit-powered chat UI
- 📄 **Multi-Format Support** - PDF, Word, HTML, CSV, Markdown, TXT
- 🔌 **REST API** - FastAPI backend for integrating with external apps
- 🏢 **Multi-Tenant** - Each client gets isolated documents and vector store
- 📤 **Document Ingestion API** - Ingest text or files per tenant
- 🔑 **API Key Auth** - Per-site access control with hashed keys
- 📊 **Plan & Usage Limits** - Per-site message limits with free/pro/gold/enterprise plans
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
- **ChromaDB** - Vector database
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
│   ├── vectorstore.py       # ChromaDB operations
│   ├── concurrency.py       # Shared semaphores (embed + upload)
│   ├── job_queue.py         # Async upload job queue, status tracking, ETA, retry
│   └── llm.py               # LLM routing (Ollama + external providers)
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
| `pro` | 2,000 | Every 30 days (rolling) | 10,000 | ~130 MB | Ollama |
| `gold` | 5,000 | Every 30 days (rolling) | 50,000 | ~650 MB | External (OpenAI / Gemini / Anthropic) |
| `enterprise` | Unlimited | — | Unlimited | — | Ollama |

Only successful `/chat` requests (HTTP 200) count toward the message quota. Storage usage and remaining capacity are returned by the `/usage` endpoint under the `storage` key.

The gold plan requires `EXTERNAL_LLM_PROVIDER` (and the matching API key) to be set before the server starts. Free, pro, and enterprise plans need no external keys.

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

### /status response

```json
{
  "status": "ok",
  "version": "1.0.0",
  "ollama": { "model": "llama3.2" },
  "external_llm": { "provider": "openai", "model": "gpt-4o-mini" }
}
```

`external_llm.provider` is `null` when `EXTERNAL_LLM_PROVIDER` is not configured.

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
| `OLLAMA_MODEL` | `llama3.2` | Model used for all Ollama-powered plans (free, pro, enterprise) |
| `EXTERNAL_LLM_PROVIDER` | *(none)* | LLM provider for the gold plan: `openai`, `gemini`, or `anthropic`. Server refuses to start if set to an unsupported value or if the matching API key is missing. |
| `EXTERNAL_LLM_MODEL` | *(provider default)* | Override the model for the external provider. Defaults: `gpt-4o-mini` (OpenAI), `gemini-2.0-flash` (Gemini), `claude-3-5-haiku-20241022` (Anthropic). |
| `OPENAI_API_KEY` | *(none)* | Required when `EXTERNAL_LLM_PROVIDER=openai` |
| `GOOGLE_API_KEY` | *(none)* | Required when `EXTERNAL_LLM_PROVIDER=gemini` |
| `ANTHROPIC_API_KEY` | *(none)* | Required when `EXTERNAL_LLM_PROVIDER=anthropic` |
| `CHROMA_DB_PATH` | `./chroma_db` | Vector store path |
| `SQLITE_DB_PATH` | `./sites.db` | SQLite database path |
| `ADMIN_SECRET` | **required** | Secret for admin endpoints. The server refuses to start if unset or set to the placeholder value. Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ALLOWED_ORIGINS` | *(none)* | Comma-separated list of allowed CORS origins, e.g. `https://app.example.com`. Leave empty to block all cross-origin requests. |
| `MAX_UPLOAD_BYTES` | `10485760` | Maximum file/text upload size in bytes (default 10 MB) |
| `EMBED_BATCH_SIZE` | `16` | Number of text chunks sent to Ollama per embedding call. Lower values reduce CPU spike; higher values increase throughput. |
| `MAX_INFLIGHT_UPLOADS` | `10` | Maximum number of upload requests actively streaming to disk at the same time. Excess requests queue in memory with negligible overhead. |

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
