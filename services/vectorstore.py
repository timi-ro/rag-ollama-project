import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = "rag_documents"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    if _collection is None:
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def upsert_chunks(site_id: int, doc_id: str, title: str, chunks: list, embeddings: list):
    collection = _get_collection()
    try:
        collection.delete(where={"$and": [{"site_id": str(site_id)}, {"doc_id": doc_id}]})
    except Exception:
        pass
    if not chunks:
        return
    ids = [f"{site_id}_{doc_id}_{i}" for i in range(len(chunks))]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"site_id": str(site_id), "doc_id": doc_id, "title": title} for _ in chunks],
    )


def query_chunks(site_id: int, embedding: list, n_results: int = 5) -> dict:
    collection = _get_collection()
    return collection.query(
        query_embeddings=[embedding],
        where={"site_id": str(site_id)},
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )


def delete_doc_chunks(site_id: int, doc_id: str):
    collection = _get_collection()
    try:
        collection.delete(where={"$and": [{"site_id": str(site_id)}, {"doc_id": doc_id}]})
    except Exception:
        pass
