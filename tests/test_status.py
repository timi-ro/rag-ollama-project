def test_health_check(client):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
