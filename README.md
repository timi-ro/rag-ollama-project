# 🤖 Local RAG System with Ollama & LangChain

A production-ready Retrieval-Augmented Generation (RAG) system built with **LangChain** and **Ollama** - completely free, no API keys required!

## ✨ Features

- 🆓 **100% Free** - No API keys, no payment methods
- 🏠 **Runs Locally** - Complete privacy, works offline
- ⚡  **Fast** - Uses Ollama's optimized local models
- 🔒 **Secure** - Your data never leaves your machine
- 📚 **Smart Document Search** - Semantic retrieval with vector embeddings
- 💬 **Interactive Chat** - Ask questions about your documents
- 🧠 **Conversation History** - Follow-up questions with context awareness
- 🌐 **Web Interface** - Streamlit-powered chat UI
- 📄 **Multi-Format Support** - Load PDFs, Word docs, HTML, CSV, Markdown, and text files
- ⚡  **Streaming Responses** - Answers stream token by token in real time
- 📎 **Source Citations** - Every answer shows which documents it came from
- 🔌 **REST API** - FastAPI backend for integrating with external apps
- 🏢 **Multi-Tenant** - Each API client gets isolated documents and vector store
- 📤 **Document Upload API** - Upload, list, and delete documents per tenant
- 💬 **Session Management** - Server-side conversation history for API clients
- 🔑 **API Key Auth** - Secure per-tenant access control

## 🛠️ Tech Stack

- **LangChain** - RAG framework
- **Ollama** - Local LLM (Llama 3.2)
- **ChromaDB** - Vector database
- **PyPDF** - PDF processing
- **Unstructured** - HTML parsing
- **Streamlit** - Web chat interface
- **FastAPI** - REST API server
- **Python 3.8+**

## 🚀 Quick Start

### Prerequisites

1. Install [Ollama](https://ollama.com)
2. Python 3.8 or higher

### Installation
```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/rag-ollama-project.git
cd rag-ollama-project

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull Ollama model (one-time, ~2GB)
ollama pull llama3.2

# 5. Run the system
python main.py
```

## 💡 Usage

### Web Interface

Launch the Streamlit chat UI:
```bash
streamlit run app.py
```

### CLI Mode

Or use the command-line interface:
```bash
python main.py
```

Example questions:
- "What is LangChain?"
- "How does retrieval work?"
- "What are the main components?"

### Add Your Own Documents

Simply drop files into the `./docs` folder and run `python main.py`. The system automatically detects and loads all supported file types:

| Format | Extensions | Use Case |
|--------|------------|----------|
| Markdown | `.md` | Documentation, notes |
| Text | `.txt` | Plain text files |
| PDF | `.pdf` | Reports, papers, manuals |
| Word | `.docx` | Documents |
| HTML | `.html`, `.htm` | Web pages |
| CSV | `.csv` | Spreadsheet data |

## 📁 Project Structure
```
rag-ollama-project/
├── main.py                  # Core RAG implementation
├── app.py                   # Streamlit web interface
├── api.py                   # FastAPI REST server
├── config.example.json      # Tenant config template
├── config.json              # Your tenant config (git-ignored)
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── .gitignore               # Git ignore rules
├── docs/{tenant}/           # Documents per tenant
├── chroma_db/{tenant}/      # Vector store per tenant (auto-generated)
└── venv/                    # Virtual environment (auto-generated)
```

## 🎯 How It Works

1. **Document Loading** - Loads content from local files in the `./docs` folder
2. **Text Splitting** - Breaks documents into manageable chunks
3. **Embedding Creation** - Converts text to vector embeddings using Ollama
4. **Vector Storage** - Stores embeddings in ChromaDB for fast retrieval
5. **Semantic Search** - Finds relevant chunks based on your question
6. **Streaming Answer** - Streams the response token by token using Llama 3.2
7. **Source Citations** - Reports which documents contributed to the answer

## 🔧 Configuration

### Using Different Models

The model can be selected per tenant in `config.json`, or switched live in the Streamlit sidebar. Pull any model first:
```bash
ollama pull mistral
```

Available models:
- `llama3.2` - Recommended (2GB)
- `mistral` - Great alternative (4GB)
- `phi3` - Lightweight and fast (2.3GB)
- `codellama` - Optimized for code (3.8GB)

### REST API Setup

```bash
# 1. Copy and fill in the config
cp config.example.json config.json

# 2. Start the API server
uvicorn api:app --reload
```

Tenant config (`config.json`):
```json
{
  "tenants": {
    "site1": { "api_key": "your-secret-key", "model": "llama3.2" },
    "site2": { "api_key": "another-key",     "model": "mistral"  }
  }
}
```

API endpoints (all require `X-API-Key` header):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Stateless chat |
| `POST` | `/chat/stream` | Streaming chat |
| `POST` | `/sessions` | Create a session |
| `DELETE` | `/sessions/{id}` | Delete a session |
| `POST` | `/sessions/{id}/chat` | Chat via session |
| `POST` | `/sessions/{id}/chat/stream` | Streaming via session |
| `POST` | `/documents/upload` | Upload a document |
| `GET` | `/documents` | List documents |
| `DELETE` | `/documents/{filename}` | Delete a document |

Interactive API docs available at `http://localhost:8000/docs`.

## 🐛 Troubleshooting

### Ollama Not Found
```bash
# Start Ollama service
ollama serve
```

### Slow First Run

First run builds the vector database (30-60 seconds). Subsequent runs are instant.

### Memory Issues

Try a smaller model:
```bash
ollama pull phi3
```

## 📝 License

MIT License - Feel free to use this for your projects!

## 👤 Author

**Fatima**
- Backend Developer | AI Enthusiast
- LinkedIn: [linkedin.com/in/frostami](https://www.linkedin.com/in/frostami/)

## 🙏 Acknowledgments

- Built with [LangChain](https://python.langchain.com/)
- Powered by [Ollama](https://ollama.com/)
- Inspired by the RAG revolution in AI

---

⭐ Star this repo if you find it useful!
