import os
from langchain_community.embeddings import OllamaEmbeddings
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "16"))

_embeddings_instance = None


def get_embeddings(model: str = None) -> OllamaEmbeddings:
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = OllamaEmbeddings(
            model=model or OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
    return _embeddings_instance


def embed_in_batches(chunks: list[str]) -> list:
    """Embed chunks in small batches to avoid saturating the CPU."""
    embedder = get_embeddings()
    results = []
    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i : i + EMBED_BATCH_SIZE]
        results.extend(embedder.embed_documents(batch))
    return results
