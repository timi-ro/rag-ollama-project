# 🤖 Local RAG System with Ollama & LangChain

A production-ready Retrieval-Augmented Generation (RAG) system built with **LangChain** and **Ollama** — completely local, no API keys required.

## ✨ Features

- 🆓 **100% Free** - No API keys, no payment methods
- 🏠 **Runs Locally** - Complete privacy, works offline
- ⚡ **Streaming Responses** - Answers stream token by token in real time
- 📎 **Source Citations** - Every answer shows which documents it came from
- 🧠 **Conversation History** - Follow-up questions with context awareness
- 🌐 **Web Interface** - Streamlit-powered chat UI
- 📄 **Multi-Format Support** - PDF, Word, HTML, CSV, Markdown, TXT
- 🔌 **REST API** - FastAPI backend for integrating with external apps
- 🏢 **Multi-Tenant** - Each client gets isolated documents and vector store
- 📤 **Document Ingestion API** - Ingest text or files per tenant
- 🔑 **API Key Auth** - Per-site access control with hashed keys
- 📊 **Plan & Usage Limits** - Per-site message limits with free/pro plans
- 🚦 **Rate Limiting** - 60 requests/minute per site
- 🐳 **Docker Support** - Full stack with one command

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
│   ├── ingest.py            # POST /ingest/text, /ingest/file, DELETE /ingest/{doc_id}
│   ├── chat.py              # POST /chat
│   └── admin.py             # Admin site management
├── services/
│   ├── embedding.py         # Ollama embeddings
│   ├── vectorstore.py       # ChromaDB operations
│   └── llm.py               # Ollama LLM
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

### Option A — Docker (Recommended)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) + Docker Compose

```bash
# 1. Clone the repository
git clone https://github.com/timi-ro/rag-ollama-project.git
cd rag-ollama-project

# 2. Start all services
docker compose up -d

# 3. Pull the Ollama model (one-time, ~2GB)
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
```

```bash
# REST API
uvicorn api:app --reload

# Streamlit UI
streamlit run app.py

# CLI
python main.py
```

## 🔧 API Reference

### Authentication

All `/ingest/*` and `/chat` endpoints require:
```
X-API-Key: <your-site-api-key>
```

Admin endpoints require:
```
X-Admin-Secret: <your-admin-secret>
```

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/status` | None | Health check |
| `POST` | `/chat` | API Key | Ask a question |
| `POST` | `/ingest/text` | API Key | Ingest raw text |
| `POST` | `/ingest/file` | API Key | Upload PDF or TXT file |
| `DELETE` | `/ingest/{doc_id}` | API Key | Delete a document |
| `POST` | `/admin/sites` | Admin | Create a site and get API key |
| `GET` | `/admin/sites` | Admin | List all sites with usage stats |
| `PATCH` | `/admin/sites/{id}/deactivate` | Admin | Deactivate a site |
| `PATCH` | `/admin/sites/{id}/plan` | Admin | Update plan and message limit |

### Example: Create a site

```bash
curl -X POST http://localhost:8000/admin/sites \
  -H "X-Admin-Secret: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-site", "plan": "free", "message_limit": 100}'
```

Returns the API key — shown only once:
```json
{ "site_id": 1, "name": "my-site", "api_key": "...", "plan": "free", "message_limit": 100 }
```

### Example: Ingest text

```bash
curl -X POST http://localhost:8000/ingest/text \
  -H "X-API-Key: <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Your content here.", "doc_id": "doc-1", "title": "Home Page"}'
```

### Example: Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What do you offer?", "conversation_history": []}'
```

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Default model |
| `CHROMA_DB_PATH` | `./chroma_db` | Vector store path |
| `SQLITE_DB_PATH` | `./sites.db` | SQLite database path |
| `ADMIN_SECRET` | `change-me-in-production` | Admin endpoint secret |
| `DEFAULT_MESSAGE_LIMIT` | `100` | Default messages per site |

## 🐛 Troubleshooting

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

## 📝 License

MIT License

## 👤 Author

**Fatima**
- Backend Developer | AI Enthusiast
- LinkedIn: [linkedin.com/in/frostami](https://www.linkedin.com/in/frostami/)

---

⭐ Star this repo if you find it useful!
