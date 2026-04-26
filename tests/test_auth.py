def test_login_success(client, seed_data):
    response = client.post(
        "/api/auth/jwt/login",
        json={"email": "user@example.com", "password": "user123"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_invalid_password(client, seed_data):
    response = client.post(
        "/api/auth/jwt/login",
        json={"email": "user@example.com", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_requires_valid_token(client, seed_data):
    response = client.get(
        "/api/auth/users/me", headers={"Authorization": "Bearer broken"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_returns_current_user(client, seed_data, auth_headers):
    response = client.get(
        "/api/auth/users/me",
        headers=auth_headers("user@example.com", "user123"),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert response.json()["is_admin"] is False
