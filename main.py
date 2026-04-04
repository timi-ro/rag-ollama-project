import os
from dataclasses import dataclass
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage

# Dedicated site_id so Streamlit data is isolated from REST API tenants
_SITE_ID = 0


@dataclass
class _RAGConfig:
    model: str
    ollama_url: str


def initialize(model: str = "llama3.2", docs_dir: str = "./docs", persist_dir: str = None) -> _RAGConfig:
    """Load all documents from docs_dir into Qdrant. Returns a config object."""
    from services.chunking import chunk_pdf, chunk_docx, chunk_text
    from services.embedding import embed_in_batches
    from services.vectorstore import upsert_chunks, delete_site_chunks

    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    print(f"Starting RAG system with model: {model}...")
    delete_site_chunks(_SITE_ID)

    docs_path = Path(docs_dir)
    if not docs_path.exists():
        print(f"Warning: Directory {docs_dir} does not exist")
        return _RAGConfig(model=model, ollama_url=ollama_url)

    supported = {".pdf", ".txt", ".md", ".docx"}
    total = 0

    for file_path in sorted(docs_path.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in supported:
            continue
        ext = file_path.suffix.lower()
        try:
            if ext == ".pdf":
                chunks = chunk_pdf(str(file_path))
            elif ext == ".docx":
                chunks = chunk_docx(str(file_path))
            else:
                chunks = chunk_text(file_path.read_text(errors="replace"), file_type=ext.lstrip("."))

            if not chunks:
                continue

            texts = [c.text for c in chunks]
            embeddings = embed_in_batches(texts)
            upsert_chunks(_SITE_ID, file_path.name, file_path.stem, chunks, embeddings)
            total += len(chunks)
            print(f"  Loaded: {file_path.name} ({len(chunks)} chunks)")
        except Exception as e:
            print(f"  Error loading {file_path.name}: {e}")

    print(f"✅ {total} chunks indexed")
    return _RAGConfig(model=model, ollama_url=ollama_url)


def _to_lc_messages(chat_history: list) -> list:
    """Convert app.py dict history to LangChain message objects."""
    out = []
    for m in chat_history:
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", "")
        content = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
    return out


def query(question: str, rag_config: _RAGConfig, chat_history: list):
    """Query Qdrant and return (answer, sources). Updates chat_history in place."""
    from services.embedding import get_embeddings
    from services.vectorstore import query_chunks
    from services.llm import _build_messages, generate_answer
    from langchain_ollama import ChatOllama

    embedding = get_embeddings().embed_query(question)
    results = query_chunks(_SITE_ID, embedding, n_results=5)
    context = "\n\n".join(results["documents"][0]) if results.get("documents") else ""
    sources = list({m["doc_id"] for m in results["metadatas"][0]}) if results.get("metadatas") else []

    llm = ChatOllama(model=rag_config.model, base_url=rag_config.ollama_url, temperature=0)
    answer = generate_answer(llm, question, context, _to_lc_messages(chat_history))

    chat_history.append({"role": "user", "content": question})
    chat_history.append({"role": "assistant", "content": answer})
    return answer, sources


def query_stream(question: str, rag_config: _RAGConfig, chat_history: list):
    """Stream the answer token by token. Yields (token, sources) tuples.

    Intermediate yields: (token_str, None)
    Final yield:         ("", sources_list)
    Updates chat_history in place.
    """
    from services.embedding import get_embeddings
    from services.vectorstore import query_chunks
    from services.llm import _build_messages
    from langchain_ollama import ChatOllama

    embedding = get_embeddings().embed_query(question)
    results = query_chunks(_SITE_ID, embedding, n_results=5)
    context = "\n\n".join(results["documents"][0]) if results.get("documents") else ""
    sources = list({m["doc_id"] for m in results["metadatas"][0]}) if results.get("metadatas") else []

    llm = ChatOllama(model=rag_config.model, base_url=rag_config.ollama_url, temperature=0)
    messages = _build_messages(question, context, _to_lc_messages(chat_history))

    full_answer = ""
    for chunk in llm.stream(messages):
        if hasattr(chunk, "content") and chunk.content:
            full_answer += chunk.content
            yield chunk.content, None

    chat_history.append({"role": "user", "content": question})
    chat_history.append({"role": "assistant", "content": full_answer})
    yield "", sources


if __name__ == "__main__":
    config = initialize()
    chat_history = []

    print("\n" + "=" * 50)
    question = "What is in the documents?"
    print(f"❓ Question: {question}")
    answer, sources = query(question, config, chat_history)
    print(f"💡 Answer: {answer}")
    print(f"📎 Sources: {', '.join(sources)}")
    print("=" * 50 + "\n")