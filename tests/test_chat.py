import pytest
from unittest.mock import MagicMock

from models.database import RequestLog
from tests.conftest import TestSession

_MOCK_QUERY_RESULT = {
    "documents": [["Relevant chunk 1", "Relevant chunk 2"]],
    "metadatas": [[{"doc_id": "doc-1"}, {"doc_id": "doc-2"}]],
}


@pytest.fixture(autouse=True)
def mock_chat_services(mocker):
    mock_emb = MagicMock()
    mock_emb.embed_query.return_value = [0.1] * 10
    mocker.patch("routers.chat.get_embeddings", return_value=mock_emb)
    mocker.patch("routers.chat.query_chunks", return_value=_MOCK_QUERY_RESULT)
    mocker.patch("routers.chat.get_llm", return_value=MagicMock())
    mocker.patch("routers.chat.generate_answer", return_value="Mocked answer")


def test_chat_happy_path(client, free_site):
    site, raw_key = free_site
    response = client.post("/chat", json={"question": "What is Python?"}, headers={"X-API-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Mocked answer"
    assert "sources" in data


def test_chat_free_limit_exceeded(client, free_site):
    site, raw_key = free_site
    session = TestSession()
    for _ in range(20):
        session.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
    session.commit()
    session.close()
    response = client.post("/chat", json={"question": "Over limit?"}, headers={"X-API-Key": raw_key})
    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "PLAN_LIMIT_REACHED"


def test_chat_429_detail_fields(client, free_site):
    site, raw_key = free_site
    session = TestSession()
    for _ in range(20):
        session.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
    session.commit()
    session.close()
    response = client.post("/chat", json={"question": "Over limit?"}, headers={"X-API-Key": raw_key})
    detail = response.json()["detail"]
    assert "plan" in detail
    assert "used" in detail
    assert "limit" in detail


def test_chat_enterprise_no_limit(client, enterprise_site):
    site, raw_key = enterprise_site
    session = TestSession()
    for _ in range(100):
        session.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
    session.commit()
    session.close()
    response = client.post("/chat", json={"question": "Unlimited?"}, headers={"X-API-Key": raw_key})
    assert response.status_code == 200


def test_chat_invalid_api_key(client):
    response = client.post("/chat", json={"question": "Hello?"}, headers={"X-API-Key": "invalidkeyXXXXXXXXXXXXXXXXXX"})
    assert response.status_code == 401


def test_chat_logs_on_success(client, free_site):
    site, raw_key = free_site
    client.post("/chat", json={"question": "Hello?"}, headers={"X-API-Key": raw_key})
    session = TestSession()
    count = session.query(RequestLog).filter(
        RequestLog.site_id == site.id,
        RequestLog.endpoint == "/chat",
        RequestLog.status_code == 200,
    ).count()
    session.close()
    assert count == 1
