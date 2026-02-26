import os
from langchain_community.embeddings import OllamaEmbeddings
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def get_embeddings(model: str = None) -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=model or OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
