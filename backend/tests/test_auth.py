import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

def unique_email():
    return f"pytest_{uuid.uuid4().hex[:8]}@example.com"

client = TestClient(app)

def test_register_new_user():
    email = unique_email()
    response = client.post("/auth/register", json={
        "email": email,
        "password": "testpass123",
        "role": "citizen"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "citizen"
    assert "password" not in data
    assert "password_hash" not in data

def test_register_duplicate_email_fails():
    email = unique_email()
    client.post("/auth/register", json={
        "email": email,
        "password": "testpass123",
        "role": "citizen"
    })
    response = client.post("/auth/register", json={
        "email": email,
        "password": "anotherpass",
        "role": "citizen"
    })
    assert response.status_code == 400

def test_login_success():
    email = unique_email()
    client.post("/auth/register", json={
        "email": email,
        "password": "testpass123",
        "role": "citizen"
    })
    response = client.post("/auth/login", json={
        "email": email,
        "password": "testpass123",
        "role": "citizen"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password_fails():
    email = unique_email()
    client.post("/auth/register", json={
        "email": email,
        "password": "correctpass",
        "role": "citizen"
    })
    response = client.post("/auth/login", json={
        "email": email,
        "password": "wrongpass",
        "role": "citizen"
    })
    assert response.status_code == 401

def test_protected_route_requires_token():
    response = client.get("/auth/me")
    assert response.status_code == 401

def test_protected_route_with_valid_token():
    email = unique_email()
    client.post("/auth/register", json={
        "email": email,
        "password": "testpass123",
        "role": "citizen"
    })
    login_response = client.post("/auth/login", json={
        "email": email,
        "password": "testpass123",
        "role": "citizen"
    })
    token = login_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == email