def test_usage_free(client, free_site):
    site, raw_key = free_site
    response = client.get("/usage", headers={"X-API-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "free"
    assert data["limit"] == 20
    assert data["used"] == 0
    assert data["remaining"] == 20
    assert data["resets_monthly"] is False


def test_usage_pro(client, pro_site):
    site, raw_key = pro_site
    response = client.get("/usage", headers={"X-API-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["resets_monthly"] is True
    assert data["limit"] == 2000


def test_usage_enterprise(client, enterprise_site):
    site, raw_key = enterprise_site
    response = client.get("/usage", headers={"X-API-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] is None
    assert data["used"] is None
    assert data["remaining"] is None
    assert data["resets_monthly"] is False


def test_usage_invalid_api_key(client):
    response = client.get("/usage", headers={"X-API-Key": "invalidkeyXXXXXXXXXXXXXXXXXX"})
    assert response.status_code == 401
