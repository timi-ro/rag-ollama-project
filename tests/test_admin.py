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


def test_list_sites(client):
    client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    response = client.get("/admin/sites", headers=ADMIN)
    assert response.status_code == 200
    data = response.json()
    assert len(data["sites"]) == 1
    assert data["sites"][0]["total_requests"] == 0


def test_deactivate_site(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.patch(f"/admin/sites/{site_id}/deactivate", headers=ADMIN)
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    session = TestSession()
    site = session.query(Site).filter(Site.id == site_id).first()
    assert site.is_active is False
    session.close()


def test_update_plan_to_pro(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.patch(f"/admin/sites/{site_id}/plan", json={"plan": "pro"}, headers=ADMIN)
    assert response.status_code == 200
    assert response.json()["message_limit"] == 2000


def test_update_plan_invalid(client):
    create_resp = client.post("/admin/sites", json={"name": "site1", "plan": "free"}, headers=ADMIN)
    site_id = create_resp.json()["site_id"]
    response = client.patch(f"/admin/sites/{site_id}/plan", json={"plan": "invalid"}, headers=ADMIN)
    assert response.status_code == 400
