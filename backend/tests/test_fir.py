import uuid
import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def unique_email():
    return f"pytest_fir_{uuid.uuid4().hex[:8]}@example.com"

def get_auth_token():
    email = unique_email()
    client.post("/auth/register", json={
        "email": email,
        "password": "testpass123",
        "role": "police"
    })
    login_response = client.post("/auth/login", json={
        "email": email,
        "password": "testpass123",
        "role": "police"
    })
    return login_response.json()["access_token"]

def test_fir_register_requires_auth():
    fake_file = io.BytesIO(b"fake pdf content")
    response = client.post(
        "/fir/register",
        files={"file": ("test.pdf", fake_file, "application/pdf")},
        params={"station_code": "PS001"},
    )
    assert response.status_code in (401, 403)

def test_fir_register_and_verify_match():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    file_content = b"this is a test fir document"
    fake_file = io.BytesIO(file_content)
    register_response = client.post(
        "/fir/register",
        files={"file": ("test.pdf", fake_file, "application/pdf")},
        params={"station_code": "PS001"},
        headers=headers,
    )
    assert register_response.status_code == 200
    fir_id = register_response.json()["fir_id"]
    assert fir_id.startswith("FIR/")

    fake_file2 = io.BytesIO(file_content)
    verify_response = client.post(
        "/fir/verify",
        files={"file": ("test.pdf", fake_file2, "application/pdf")},
        params={"fir_id": fir_id},
        headers=headers,
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["match"] is True

def test_fir_verify_detects_tampering():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    original_file = io.BytesIO(b"original document content")
    register_response = client.post(
        "/fir/register",
        files={"file": ("test.pdf", original_file, "application/pdf")},
        params={"station_code": "PS001"},
        headers=headers,
    )
    fir_id = register_response.json()["fir_id"]

    tampered_file = io.BytesIO(b"TAMPERED document content")
    verify_response = client.post(
        "/fir/verify",
        files={"file": ("test.pdf", tampered_file, "application/pdf")},
        params={"fir_id": fir_id},
        headers=headers,
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["match"] is False

def test_fir_verify_nonexistent_id():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    fake_file = io.BytesIO(b"some content")
    response = client.post(
        "/fir/verify",
        files={"file": ("test.pdf", fake_file, "application/pdf")},
        params={"fir_id": "FIR/FAKE/9999/PS999/00000"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["match"] is False