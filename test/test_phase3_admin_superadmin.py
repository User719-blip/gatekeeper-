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


def test_superadmin_can_promote_admin(client):
    register_admin(client, "root", "StrongPass123")      # bootstrap superadmin
    register_admin(client, "admin2", "StrongPass123")    # normal admin

    super_token = login_admin(client, "root", "StrongPass123").json()["access_token"]

    promote_resp = client.post(
        "/admin/promote/admin2",
        headers=auth_header(super_token),
    )
    assert promote_resp.status_code == 200

    # admin2 should now be able to do superadmin-only delete
    apply_resp = client.post("/apply", json={"name": "x", "description": "y"})
    app_id = apply_resp.json()["id"]

    promoted_token = login_admin(client, "admin2", "StrongPass123").json()["access_token"]
    delete_resp = client.delete(f"/delete/{app_id}", headers=auth_header(promoted_token))
    assert delete_resp.status_code == 200


def test_admin_cannot_promote(client):
    register_admin(client, "root", "StrongPass123")
    register_admin(client, "admin2", "StrongPass123")
    register_admin(client, "admin3", "StrongPass123")

    admin_token = login_admin(client, "admin2", "StrongPass123").json()["access_token"]

    resp = client.post("/admin/promote/admin3", headers=auth_header(admin_token))
    assert resp.status_code == 403


def test_superadmin_can_remove_admin(client):
    register_admin(client, "root", "StrongPass123")
    register_admin(client, "admin2", "StrongPass123")

    super_token = login_admin(client, "root", "StrongPass123").json()["access_token"]

    remove_resp = client.delete("/admin/remove/admin2", headers=auth_header(super_token))
    assert remove_resp.status_code == 200

    # removed admin can no longer login
    login_resp = login_admin(client, "admin2", "StrongPass123")
    assert login_resp.status_code == 401


def test_cannot_remove_last_superadmin(client):
    register_admin(client, "root", "StrongPass123")
    super_token = login_admin(client, "root", "StrongPass123").json()["access_token"]

    remove_resp = client.delete("/admin/remove/root", headers=auth_header(super_token))
    assert remove_resp.status_code == 400