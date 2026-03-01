from models.database import Site
from tests.conftest import TestSession


def test_valid_api_key(client, free_site):
    site, raw_key = free_site
    response = client.get("/usage", headers={"X-API-Key": raw_key})
    assert response.status_code == 200


def test_invalid_api_key(client):
    response = client.get("/usage", headers={"X-API-Key": "invalidkeyXXXXXXXXXXXXXXXXXX"})
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "INVALID_API_KEY"


def test_missing_api_key(client):
    response = client.get("/usage")
    assert response.status_code == 422


def test_inactive_site_rejected(client, free_site):
    site, raw_key = free_site
    session = TestSession()
    db_site = session.query(Site).filter(Site.id == site.id).first()
    db_site.is_active = False
    session.commit()
    session.close()
    response = client.get("/usage", headers={"X-API-Key": raw_key})
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "INVALID_API_KEY"


def test_valid_admin_secret(client):
    response = client.get("/admin/sites", headers={"X-Admin-Secret": "test-secret"})
    assert response.status_code == 200


def test_invalid_admin_secret(client):
    response = client.get("/admin/sites", headers={"X-Admin-Secret": "wrong-secret"})
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "INVALID_ADMIN_SECRET"
