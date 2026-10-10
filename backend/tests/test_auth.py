import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User


def unique_email() -> str:
    return f"pytest_{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
def auth_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(auth_database):
    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, email: str, password: str = "testpass123"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "role": "citizen"},
    )


def login(client: TestClient, email: str, password: str, role: str):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password, "role": role},
    )


def test_register_normalizes_email_and_hashes_password(client, auth_database):
    email = unique_email()
    response = register(client, email.upper())

    assert response.status_code == 200
    assert response.json()["email"] == email
    assert "password" not in response.json()
    assert "password_hash" not in response.json()

    db = auth_database()
    try:
        user = db.query(User).filter(User.email == email).one()
        assert user.password_hash != "testpass123"
        assert user.password_hash.startswith("$2")
    finally:
        db.close()


def test_duplicate_registration_is_case_insensitive(client):
    email = unique_email()
    assert register(client, email).status_code == 200
    assert register(client, email.upper()).status_code == 400


@pytest.mark.parametrize("role", ["police", "lawyer", "admin"])
def test_public_registration_cannot_create_privileged_accounts(client, role):
    response = client.post(
        "/auth/register",
        json={"email": unique_email(), "password": "testpass123", "role": role},
    )
    assert response.status_code == 403


def test_login_sets_httponly_session_cookie_and_restores_session(client):
    email = unique_email()
    assert register(client, email).status_code == 200

    response = login(client, email, "testpass123", "citizen")
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "lawaid_token=" in response.headers["set-cookie"]

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_login_rejects_wrong_password_unknown_email_and_portal_mismatch(client, auth_database):
    email = unique_email()
    assert register(client, email).status_code == 200
    assert login(client, email, "wrongpass", "citizen").status_code == 401
    assert login(client, unique_email(), "testpass123", "citizen").status_code == 401

    db = auth_database()
    try:
        police_email = unique_email()
        db.add(User(email=police_email, password_hash=hash_password("testpass123"), role="police"))
        db.commit()
    finally:
        db.close()
    assert login(client, police_email, "testpass123", "citizen").status_code == 403


def test_protected_routes_enforce_authentication_and_database_roles(client, auth_database):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/fir/drafts").status_code == 401

    citizen_email = unique_email()
    assert register(client, citizen_email).status_code == 200
    citizen_token = login(client, citizen_email, "testpass123", "citizen").json()["access_token"]
    assert client.get("/fir/drafts", headers={"Authorization": f"Bearer {citizen_token}"}).status_code == 403

    db = auth_database()
    try:
        police_email = unique_email()
        lawyer_email = unique_email()
        db.add_all([
            User(email=police_email, password_hash=hash_password("testpass123"), role="police"),
            User(email=lawyer_email, password_hash=hash_password("testpass123"), role="lawyer"),
        ])
        db.commit()
    finally:
        db.close()

    police_token = login(client, police_email, "testpass123", "police").json()["access_token"]
    lawyer_token = login(client, lawyer_email, "testpass123", "lawyer").json()["access_token"]
    assert client.get("/fir/drafts", headers={"Authorization": f"Bearer {police_token}"}).status_code == 200
    assert client.get("/fir/drafts", headers={"Authorization": f"Bearer {lawyer_token}"}).status_code == 403


def test_logout_invalidates_browser_session_cookie(client):
    email = unique_email()
    assert register(client, email).status_code == 200
    assert login(client, email, "testpass123", "citizen").status_code == 200
    assert client.get("/auth/me").status_code == 200

    response = client.post("/auth/logout")
    assert response.status_code == 200
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert client.get("/auth/me").status_code == 401


def test_forgot_password_is_generic_and_never_returns_a_reset_token(client):
    for email in [unique_email(), "missing_" + unique_email()]:
        response = client.post("/auth/forgot-password", json={"email": email})
        assert response.status_code == 200
        assert response.json() == {
            "message": "If that email is registered, password reset instructions will be sent."
        }


def test_invalid_token_is_rejected(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
    assert response.status_code == 401
