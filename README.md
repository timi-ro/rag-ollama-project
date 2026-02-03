# 🤖 Local RAG System with Ollama & LangChain

A production-ready Retrieval-Augmented Generation (RAG) system built with **LangChain** and **Ollama** - completely free, no API keys required!

## ✨ Features

- 🆓 **100% Free** - No API keys, no payment methods
- 🏠 **Runs Locally** - Complete privacy, works offline
- ⚡ **Fast** - Uses Ollama's optimized local models
- 🔒 **Secure** - Your data never leaves your machine
- 📚 **Smart Document Search** - Semantic retrieval with vector embeddings
- 💬 **Interactive Chat** - Ask questions about your documents
- 📄 **Multi-Format Support** - Load PDFs, Word docs, HTML, CSV, Markdown, and text files

## 🛠️ Tech Stack

- **LangChain** - RAG framework
- **Ollama** - Local LLM (Llama 3.2)
- **ChromaDB** - Vector database
- **PyPDF** - PDF processing
- **Unstructured** - HTML parsing
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

### Interactive Mode

Simply run the script and ask questions:
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
├── main.py              # Core RAG implementation
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── .gitignore          # Git ignore rules
├── docs/               # Your documents go here
├── chroma_db/          # Vector database (auto-generated)
└── venv/               # Virtual environment (auto-generated)
```

## 🎯 How It Works

1. **Document Loading** - Loads content from web or local files
2. **Text Splitting** - Breaks documents into manageable chunks
3. **Embedding Creation** - Converts text to vector embeddings using Ollama
4. **Vector Storage** - Stores embeddings in ChromaDB for fast retrieval
5. **Semantic Search** - Finds relevant chunks based on your question
6. **Answer Generation** - Uses Llama 3.2 to generate contextual answers

## 🔧 Configuration

### Using Different Models

Ollama supports multiple models. To use a different one:
```bash
# Pull a different model
ollama pull mistral

# Update main.py
llm = Ollama(model="mistral", temperature=0)
embeddings = OllamaEmbeddings(model="mistral")
```

Available models:
- `llama3.2` - Recommended (2GB)
- `mistral` - Great alternative (4GB)
- `phi3` - Lightweight and fast (2.3GB)
- `codellama` - Optimized for code (3.8GB)

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
