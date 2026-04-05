import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    FilterSelector, PayloadSchemaType,
)

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "rag_documents"
EMBED_DIM = int(os.getenv("EMBED_DIM", "3072"))  # llama3.2 default

_UUID_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # stable namespace

_client = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
        if not _client.collection_exists(COLLECTION_NAME):
            _client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
            )
            _client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="site_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
    return _client


def _point_id(site_id: int, doc_id: str, chunk_index: int) -> str:
    """Deterministic UUID from the logical chunk identifier."""
    return str(uuid.uuid5(_UUID_NS, f"{site_id}_{doc_id}_{chunk_index}"))


def _site_filter(site_id: int) -> Filter:
    return Filter(must=[FieldCondition(key="site_id", match=MatchValue(value=str(site_id)))])


def _doc_filter(site_id: int, doc_id: str) -> Filter:
    return Filter(must=[
        FieldCondition(key="site_id", match=MatchValue(value=str(site_id))),
        FieldCondition(key="doc_id",  match=MatchValue(value=doc_id)),
    ])


def upsert_chunks(site_id: int, doc_id: str, title: str, chunks: list, embeddings: list):
    client = _get_client()
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=FilterSelector(filter=_doc_filter(site_id, doc_id)),
    )
    if not chunks:
        return
    points = [
        PointStruct(
            id=_point_id(site_id, doc_id, i),
            vector=embeddings[i],
            payload={
                "site_id":        str(site_id),
                "doc_id":         doc_id,
                "title":          title,
                "text":           chunk.text,
                "file_type":      chunk.file_type,
                "page":           chunk.page,
                "section_title":  chunk.section_title,
            },
        )
        for i, chunk in enumerate(chunks)
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)


def query_chunks(site_id: int, embedding: list, n_results: int = 5,
                 doc_id: Optional[str] = None, file_type: Optional[str] = None) -> dict:
    client = _get_client()
    conditions = [FieldCondition(key="site_id", match=MatchValue(value=str(site_id)))]
    if doc_id:
        conditions.append(FieldCondition(key="doc_id", match=MatchValue(value=doc_id)))
    if file_type:
        conditions.append(FieldCondition(key="file_type", match=MatchValue(value=file_type)))
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=embedding,
        query_filter=Filter(must=conditions),
        limit=n_results,
        with_payload=True,
    )
    results = response.points
    documents = [[r.payload["text"] for r in results]]
    metadatas = [[{
        "doc_id":        r.payload["doc_id"],
        "title":         r.payload.get("title", ""),
        "page":          r.payload.get("page"),
        "section_title": r.payload.get("section_title"),
        "file_type":     r.payload.get("file_type", "text"),
    } for r in results]]
    distances = [[r.score for r in results]]
    return {"documents": documents, "metadatas": metadatas, "distances": distances}


def list_docs(site_id: int) -> list:
    client = _get_client()
    seen = {}
    offset = None
    while True:
        batch, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=_site_filter(site_id),
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in batch:
            doc_id = point.payload["doc_id"]
            if doc_id not in seen:
                seen[doc_id] = {"doc_id": doc_id, "title": point.payload.get("title", ""), "file_type": point.payload.get("file_type", "text"), "chunk_count": 0}
            seen[doc_id]["chunk_count"] += 1
        if offset is None:
            break
    return list(seen.values())


def count_chunks(site_id: int) -> int:
    client = _get_client()
    return client.count(
        collection_name=COLLECTION_NAME,
        count_filter=_site_filter(site_id),
        exact=True,
    ).count


def count_doc_chunks(site_id: int, doc_id: str) -> int:
    client = _get_client()
    return client.count(
        collection_name=COLLECTION_NAME,
        count_filter=_doc_filter(site_id, doc_id),
        exact=True,
    ).count


def delete_doc_chunks(site_id: int, doc_id: str):
    client = _get_client()
    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(filter=_doc_filter(site_id, doc_id)),
        )
    except Exception:
        logger.warning("Failed to delete chunks for doc %s (site %s)", doc_id, site_id, exc_info=True)


def delete_site_chunks(site_id: int):
    client = _get_client()
    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(filter=_site_filter(site_id)),
        )
    except Exception:
        logger.warning("Failed to delete chunks for site %s", site_id, exc_info=True)