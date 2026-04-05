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


def test_bootstrap_first_admin_becomes_superadmin(client):
    response = register_admin(client, "root", "StrongPass123")
    assert response.status_code == 200
    assert response.json()["message"] == "Admin created as superadmin"

    login = login_admin(client, "root", "StrongPass123")
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_second_admin_is_normal_admin(client):
    register_admin(client, "root", "StrongPass123")
    response = register_admin(client, "admin2", "StrongPass123")
    assert response.status_code == 200
    assert response.json()["message"] == "Admin created as admin"


def test_apply_and_admin_approval_flow(client):
    register_admin(client, "root", "StrongPass123")
    register_admin(client, "admin2", "StrongPass123")

    login = login_admin(client, "admin2", "StrongPass123")
    token = login.json()["access_token"]

    apply_resp = client.post(
        "/apply",
        json={"name": "aryan", "description": "testing"},
    )
    assert apply_resp.status_code == 201
    application_id = apply_resp.json()["id"]

    list_resp = client.get("/applications", headers=auth_header(token))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    approve_resp = client.patch(
        f"/approve/{application_id}",
        headers=auth_header(token),
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["is_approved"] is True


def test_admin_cannot_delete_but_superadmin_can(client):
    register_admin(client, "root", "StrongPass123")
    register_admin(client, "admin2", "StrongPass123")

    super_login = login_admin(client, "root", "StrongPass123")
    admin_login = login_admin(client, "admin2", "StrongPass123")

    apply_resp = client.post(
        "/apply",
        json={"name": "aryan", "description": "testing"},
    )
    application_id = apply_resp.json()["id"]

    admin_delete = client.delete(
        f"/delete/{application_id}",
        headers=auth_header(admin_login.json()["access_token"]),
    )
    assert admin_delete.status_code == 403

    super_delete = client.delete(
        f"/delete/{application_id}",
        headers=auth_header(super_login.json()["access_token"]),
    )
    assert super_delete.status_code == 200