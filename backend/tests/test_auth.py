from fastapi.testclient import TestClient


def test_login_and_current_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin123!"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["role"] == "ADMIN"

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_invalid_login(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_change_password(client: TestClient):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin123!"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    wrong = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "NewAdmin123!"},
        headers=headers,
    )
    assert wrong.status_code == 400

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Admin123!", "new_password": "NewAdmin123!"},
        headers=headers,
    )
    assert changed.status_code == 200

    old_login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin123!"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "NewAdmin123!"},
    )
    assert new_login.status_code == 200
