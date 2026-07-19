import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_student_care.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-tests")
os.environ.setdefault("INITIAL_ADMIN_USERNAME", "admin")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "Admin123!")
os.environ.setdefault("INITIAL_ADMIN_NAME", "测试管理员")
os.environ.setdefault("AUTO_CREATE_TABLES", "true")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    initialize_database()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin123!"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_base_people(client: TestClient, headers: dict[str, str]):
    org = client.post(
        "/api/v1/organizations",
        json={"code": "CS", "name": "计算机学院"},
        headers=headers,
    )
    assert org.status_code == 201, org.text
    org_id = org.json()["id"]

    counselor = client.post(
        "/api/v1/users",
        json={
            "username": "counselor1",
            "password": "Counselor123!",
            "full_name": "张辅导员",
            "role": "COUNSELOR",
            "organization_id": org_id,
        },
        headers=headers,
    )
    assert counselor.status_code == 201, counselor.text

    psychologist = client.post(
        "/api/v1/users",
        json={
            "username": "psych1",
            "password": "Psychologist123!",
            "full_name": "李老师",
            "role": "PSYCHOLOGIST",
            "organization_id": None,
        },
        headers=headers,
    )
    assert psychologist.status_code == 201, psychologist.text
    return org.json(), counselor.json(), psychologist.json()


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
