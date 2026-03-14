import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def mock_ingest_services(mocker):
    mocker.patch("routers.ingest.embed_in_batches", return_value=[[0.1] * 10])
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


def test_ingest_file_returns_202_with_job_id(client, free_site):
    site, raw_key = free_site
    response = client.post(
        "/ingest/file",
        files={"file": ("document.txt", b"This is file content. " * 60, "text/plain")},
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert "poll_url" in data


def test_poll_status_unknown_job(client, free_site):
    site, raw_key = free_site
    response = client.get("/ingest/status/j_doesnotexist", headers={"X-API-Key": raw_key})
    assert response.status_code == 404


def test_poll_status_known_job(client, free_site):
    site, raw_key = free_site
    upload_resp = client.post(
        "/ingest/file",
        files={"file": ("document.txt", b"Hello world. " * 60, "text/plain")},
        headers={"X-API-Key": raw_key},
    )
    job_id = upload_resp.json()["job_id"]
    response = client.get(f"/ingest/status/{job_id}", headers={"X-API-Key": raw_key})
    assert response.status_code == 200
    assert response.json()["job_id"] == job_id
    assert response.json()["filename"] == "document.txt"


def test_retry_unknown_job_returns_404(client, free_site):
    site, raw_key = free_site
    response = client.post("/ingest/retry/j_doesnotexist", headers={"X-API-Key": raw_key})
    assert response.status_code == 404


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
