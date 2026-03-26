import pytest

from services.chunking import Chunk
from services.retrieval_eval import mrr, recall_at_k
from services.vectorstore import upsert_chunks, query_chunks


# ---------------------------------------------------------------------------
# Metric unit tests
# ---------------------------------------------------------------------------

def test_mrr_hit_at_rank_1():
    assert mrr(["a"], ["a", "b", "c"]) == pytest.approx(1.0)


def test_mrr_hit_at_rank_2():
    assert mrr(["b"], ["a", "b", "c"]) == pytest.approx(0.5)


def test_mrr_no_hit():
    assert mrr(["x"], ["a", "b", "c"]) == pytest.approx(0.0)


def test_mrr_multiple_relevant_uses_first_match():
    # "b" appears at rank 2, "a" at rank 3 — first hit is rank 2
    assert mrr(["a", "b"], ["c", "b", "a"]) == pytest.approx(0.5)


def test_recall_at_k_full():
    assert recall_at_k(["a", "b"], ["a", "b", "c"], k=2) == pytest.approx(1.0)


def test_recall_at_k_partial():
    assert recall_at_k(["a", "b"], ["a", "c", "d"], k=3) == pytest.approx(0.5)


def test_recall_at_k_none_found():
    assert recall_at_k(["x"], ["a", "b", "c"], k=3) == pytest.approx(0.0)


def test_recall_at_k_empty_relevant():
    assert recall_at_k([], ["a", "b"], k=2) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Integration: insert chunks with known embeddings, measure retrieval quality
# ---------------------------------------------------------------------------

def test_retrieval_quality_with_known_embeddings():
    """
    Insert 3 chunks with orthogonal unit vectors.
    Query with vector 0 → chunk 0 should rank first → MRR=1.0, Recall@1=1.0.
    """
    chunks = [
        Chunk(text="Python is a programming language", file_type="text"),
        Chunk(text="The sky is blue on a clear day", file_type="text"),
        Chunk(text="Machine learning uses statistics", file_type="text"),
    ]
    embeddings = [
        [1.0] + [0.0] * 9,
        [0.0, 1.0] + [0.0] * 8,
        [0.0, 0.0, 1.0] + [0.0] * 7,
    ]
    upsert_chunks(999, "eval-doc", "Eval Doc", chunks, embeddings)

    results = query_chunks(999, [1.0] + [0.0] * 9, n_results=3)
    retrieved_texts = results["documents"][0]

    assert retrieved_texts[0] == "Python is a programming language"
    assert mrr(["Python is a programming language"], retrieved_texts) == pytest.approx(1.0)
    assert recall_at_k(["Python is a programming language"], retrieved_texts, k=1) == pytest.approx(1.0)

    # Verify richer metadata fields are present
    meta = results["metadatas"][0][0]
    assert meta["doc_id"] == "eval-doc"
    assert meta["file_type"] == "text"
    assert "page" in meta
    assert "section_title" in meta


def test_retrieval_doc_filter():
    """Filtering by doc_id should only return chunks from that document."""
    chunks_a = [Chunk(text="Alpha document content here", file_type="text")]
    chunks_b = [Chunk(text="Beta document content is different", file_type="text")]
    emb = [[0.5] * 10]

    upsert_chunks(998, "doc-alpha", "Alpha", chunks_a, emb)
    upsert_chunks(998, "doc-beta", "Beta", chunks_b, emb)

    results = query_chunks(998, [0.5] * 10, n_results=5, doc_id="doc-alpha")
    assert len(results["documents"][0]) >= 1
    for meta in results["metadatas"][0]:
        assert meta["doc_id"] == "doc-alpha"


def test_retrieval_file_type_filter():
    """Filtering by file_type should only return chunks of that type."""
    pdf_chunks = [Chunk(text="PDF content here", file_type="pdf", page=1)]
    txt_chunks = [Chunk(text="Text content here", file_type="text")]
    emb = [[0.7] * 10]

    upsert_chunks(997, "mixed-pdf", "Mixed PDF", pdf_chunks, emb)
    upsert_chunks(997, "mixed-txt", "Mixed Text", txt_chunks, emb)

    results = query_chunks(997, [0.7] * 10, n_results=5, file_type="pdf")
    assert len(results["documents"][0]) >= 1
    for meta in results["metadatas"][0]:
        assert meta["file_type"] == "pdf"