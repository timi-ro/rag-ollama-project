import bcrypt
import pytest
from models.database import Site
from tests.conftest import TestSession

ADMIN = {"X-Admin-Secret": "test-secret"}


def test_create_site_free(client):
    response = client.post("/admin/sites", json={"name": "mysite", "plan": "free"}, headers=ADMIN)
    assert response.status_code == 200
    data = response.json()
    assert data["message_limit"] == 20
    assert "api_key" in data


def test_create_site_pro(client):
    response = client.post("/admin/sites", json={"name": "mysite", "plan": "pro"}, headers=ADMIN)
    assert response.status_code == 200
    assert response.json()["message_limit"] == 2000


def test_create_site_enterprise(client):
    response = client.post("/admin/sites", json={"name": "mysite", "plan": "enterprise"}, headers=ADMIN)
    assert response.status_code == 200
    assert response.json()["message_limit"] is None


def test_create_site_invalid_plan(client):
    response = client.post("/admin/sites", json={"name": "mysite", "plan": "invalid"}, headers=ADMIN)
    assert response.status_code == 400


def test_create_site_duplicate_name(client):
    client.post("/admin/sites", json={"name": "mysite", "plan": "free"}, headers=ADMIN)
    response = client.post("/admin/sites", json={"name": "mysite", "plan": "pro"}, headers=ADMIN)
    assert response.status_code == 409


def test_list_sites(client):
    client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    response = client.get("/admin/sites", headers=ADMIN)
    assert response.status_code == 200
    data = response.json()
    assert len(data["sites"]) == 1
    assert data["sites"][0]["total_requests"] == 0


def test_update_site_plan(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.patch(f"/admin/sites/{site_id}", json={"plan": "pro"}, headers=ADMIN)
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "pro"
    assert data["message_limit"] == 2000


def test_update_site_deactivate(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.patch(f"/admin/sites/{site_id}", json={"is_active": False}, headers=ADMIN)
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_update_site_reactivate(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    client.patch(f"/admin/sites/{site_id}", json={"is_active": False}, headers=ADMIN)
    response = client.patch(f"/admin/sites/{site_id}", json={"is_active": True}, headers=ADMIN)
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_update_site_plan_and_status_together(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.patch(f"/admin/sites/{site_id}", json={"plan": "pro", "is_active": False}, headers=ADMIN)
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "pro"
    assert data["is_active"] is False


def test_update_site_nothing_returns_400(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.patch(f"/admin/sites/{site_id}", json={}, headers=ADMIN)
    assert response.status_code == 400


def test_update_site_invalid_plan(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.patch(f"/admin/sites/{site_id}", json={"plan": "invalid"}, headers=ADMIN)
    assert response.status_code == 400


def test_reset_messages(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.post(f"/admin/sites/{site_id}/reset", json={"messages": True}, headers=ADMIN)
    assert response.status_code == 200
    assert "messages" in response.json()["cleared"]


def test_reset_files(client, mocker):
    mocker.patch("routers.admin.delete_site_chunks")
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.post(f"/admin/sites/{site_id}/reset", json={"files": True}, headers=ADMIN)
    assert response.status_code == 200
    assert "files" in response.json()["cleared"]


def test_reset_nothing_returns_400(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.post(f"/admin/sites/{site_id}/reset", json={}, headers=ADMIN)
    assert response.status_code == 400


def test_regenerate_key(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    old_key = create_resp.json()["api_key"]
    response = client.post(f"/admin/sites/{site_id}/regenerate-key", headers=ADMIN)
    assert response.status_code == 200
    new_key = response.json()["api_key"]
    assert new_key != old_key
    # old key should now be rejected
    chat_resp = client.post("/chat", json={"question": "hi"}, headers={"X-API-Key": old_key})
    assert chat_resp.status_code == 401