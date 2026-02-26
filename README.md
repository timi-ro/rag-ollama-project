# 🤖 Local RAG System with Ollama & LangChain

A production-ready Retrieval-Augmented Generation (RAG) system built with **LangChain** and **Ollama** - completely local, no API keys required!

## ✨ Features

- 🆓 **100% Free** - No API keys, no payment methods
- 🏠 **Runs Locally** - Complete privacy, works offline
- ⚡ **Fast** - Uses Ollama's optimized local models
- 🔒 **Secure** - Your data never leaves your machine
- 📚 **Smart Document Search** - Semantic retrieval with vector embeddings
- 💬 **Interactive Chat** - Ask questions about your documents
- 🧠 **Conversation History** - Follow-up questions with context awareness
- 🌐 **Web Interface** - Streamlit-powered chat UI
- 📄 **Multi-Format Support** - Load PDFs, Word docs, HTML, CSV, Markdown, and text files
- ⚡ **Streaming Responses** - Answers stream token by token in real time
- 📎 **Source Citations** - Every answer shows which documents it came from
- 🔌 **REST API** - FastAPI backend for integrating with external apps
- 🏢 **Multi-Tenant** - Each site gets isolated documents and vector store
- 📤 **Document Ingestion API** - Ingest text or files per tenant via API
- 🔑 **API Key Auth** - Secure per-site access control with hashed keys
- 📊 **Plan & Usage Limits** - Per-site message limits with free/pro plans
- 🚦 **Rate Limiting** - 60 requests/minute per site

## 🛠️ Tech Stack

- **LangChain** - RAG framework
- **Ollama** - Local LLM (Llama 3.2)
- **ChromaDB** - Vector database
- **FastAPI** - REST API server
- **SQLAlchemy + SQLite** - Site metadata and request logging
- **slowapi** - Rate limiting
- **Streamlit** - Web chat interface
- **PyPDF** - PDF processing
- **Python 3.10+**

## 📁 Project Structure

```
rag-ollama-project/
├── api.py                   # FastAPI app entry point
├── main.py                  # Local CLI usage
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
│   └── auth.py              # API key + admin auth dependencies
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
└── chroma_db/               # Vector database (auto-generated)
```

## 🚀 Quick Start

### Prerequisites

1. Install [Ollama](https://ollama.com)
2. Python 3.10 or higher

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/timi-ro/rag-ollama-project.git
cd rag-ollama-project

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull Ollama model
ollama pull llama3.2
```

## 💡 Usage

### Web Interface

```bash
streamlit run app.py
```

### CLI Mode

```bash
python main.py
```

### REST API

```bash
# 1. Set up environment
cp .env.example .env   # edit values as needed

# 2. Start the server
uvicorn api:app --reload
```

The database is created automatically on first startup. Interactive docs at `http://localhost:8000/docs`.

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
| `POST` | `/admin/sites` | Admin | Create a site + get API key |
| `GET` | `/admin/sites` | Admin | List all sites with usage |
| `PATCH` | `/admin/sites/{id}/deactivate` | Admin | Deactivate a site |
| `PATCH` | `/admin/sites/{id}/plan` | Admin | Update plan and message limit |

### Example: Create a site

```bash
curl -X POST http://localhost:8000/admin/sites \
  -H "X-Admin-Secret: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-wordpress-site", "plan": "pro", "message_limit": 1000}'
```

Returns the API key (shown only once):
```json
{
  "site_id": 1,
  "name": "my-wordpress-site",
  "api_key": "...",
  "plan": "pro",
  "message_limit": 1000
}
```

### Example: Ingest content

```bash
curl -X POST http://localhost:8000/ingest/text \
  -H "X-API-Key: <site-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Your page content...", "doc_id": "page-123", "title": "About Us"}'
```

### Example: Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: <site-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What services do you offer?", "conversation_history": []}'
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

### Ollama Not Running
```bash
ollama serve
```

### Model Not Found
```bash
ollama pull llama3.2
```

### Slow First Request

First request per site builds the vector index. Subsequent requests are fast.

## 📝 License

MIT License - Feel free to use this for your projects!

## 👤 Author

**Fatima**
- Backend Developer | AI Enthusiast
- LinkedIn: [linkedin.com/in/frostami](https://www.linkedin.com/in/frostami/)

## 🙏 Acknowledgments

- Built with [LangChain](https://python.langchain.com/)
- Powered by [Ollama](https://ollama.com/)

---

⭐ Star this repo if you find it useful!
