import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def mock_ingest_services(mocker):
    mock_emb = MagicMock()
    mock_emb.embed_documents.side_effect = lambda chunks: [[0.1] * 10 for _ in chunks]
    mocker.patch("routers.ingest.get_embeddings", return_value=mock_emb)
    mocker.patch("routers.ingest.upsert_chunks")
    mocker.patch("routers.ingest.delete_doc_chunks")
    mocker.patch("routers.ingest.list_docs", return_value=[{"doc_id": "doc-1", "title": "Test Doc"}])


def test_ingest_text_happy_path(client, free_site):
    site, raw_key = free_site
    response = client.post(
        "/ingest/text",
        json={"content": "This is some content. " * 60, "doc_id": "doc-1", "title": "Test"},
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 200
    assert response.json()["ingested"] > 0


def test_ingest_text_empty_produces_400(client, free_site):
    site, raw_key = free_site
    response = client.post(
        "/ingest/text",
        json={"content": "   ", "doc_id": "doc-1"},
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 400


def test_ingest_file_unsupported_extension(client, free_site):
    site, raw_key = free_site
    response = client.post(
        "/ingest/file",
        files={"file": ("document.docx", b"some content", "application/octet-stream")},
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 400


def test_ingest_file_too_large(client, free_site):
    site, raw_key = free_site
    large_content = b"x" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/ingest/file",
        files={"file": ("document.txt", large_content, "text/plain")},
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 413


def test_ingest_file_txt(client, free_site, mocker):
    site, raw_key = free_site
    mock_doc = MagicMock()
    mock_doc.page_content = "This is file content. " * 60
    mock_loader = MagicMock()
    mock_loader.load.return_value = [mock_doc]
    mocker.patch("routers.ingest.TextLoader", return_value=mock_loader)
    response = client.post(
        "/ingest/file",
        files={"file": ("document.txt", b"This is file content. " * 60, "text/plain")},
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 200
    assert response.json()["ingested"] > 0


def test_list_documents(client, free_site):
    site, raw_key = free_site
    response = client.get("/ingest/documents", headers={"X-API-Key": raw_key})
    assert response.status_code == 200
    assert "documents" in response.json()


def test_delete_document(client, free_site):
    site, raw_key = free_site
    response = client.delete("/ingest/doc-1", headers={"X-API-Key": raw_key})
    assert response.status_code == 200
    assert response.json()["deleted"] == "doc-1"
