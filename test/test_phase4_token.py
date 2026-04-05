import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from db.database import Base
from db.deps import get_db


TEST_DATABASE_URL = "sqlite://"


@pytest.fixture()
def client():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def register_admin(client, username, password):
    return client.post(
        "/admin/register",
        headers={"x-api-key": "my123"},
        json={"username": username, "password": password},
    )


def login_admin(client, username, password):
    return client.post(
        "/admin/login",
        json={"username": username, "password": password},
    )


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_access_and_refresh_tokens(client):
    register_admin(client, "root", "StrongPass123")

    response = login_admin(client, "root", "StrongPass123")
    assert response.status_code == 200

    body = response.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body
    assert "refresh_token" in body


def test_refresh_returns_new_access_token(client):
    register_admin(client, "root", "StrongPass123")

    login_response = login_admin(client, "root", "StrongPass123")
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/admin/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200

    body = refresh_response.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body


def test_logout_revokes_refresh_token(client):
    register_admin(client, "root", "StrongPass123")

    login_response = login_admin(client, "root", "StrongPass123")
    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post(
        "/admin/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_response.status_code == 200

    refresh_response = client.post(
        "/admin/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


def test_refresh_token_cannot_access_protected_routes(client):
    register_admin(client, "root", "StrongPass123")

    login_response = login_admin(client, "root", "StrongPass123")
    refresh_token = login_response.json()["refresh_token"]

    response = client.get(
        "/applications",
        headers=auth_header(refresh_token),
    )
    assert response.status_code == 401