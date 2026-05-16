def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "error" in response.json() or "detail" in response.json()


def test_me_returns_user(auth_client):
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "00000000-0000-0000-0000-000000000001"
    assert data["email"] == "test@example.com"
