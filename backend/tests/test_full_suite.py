import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_bns_search():
    res = client.get("/fir/bns/search?query=someone cheated me of money")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["ok", "insufficient_information"]
    assert "results" in data


def test_incident_analysis():
    res = client.post("/fir/analyze", json={"incident": "Accused took my gold chain and ran away on a motorcycle near the market."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "data" in data
    assert "analysis" in data["data"]
    assert len(data["data"]["analysis"]) > 0


def test_fir_generate():
    res = client.post("/fir/generate", json={"complaint": "Theft of mobile device", "station_code": "PS001"})
    assert res.status_code == 200
    data = res.json()
    assert "fir_id" in data
    assert data["status"] == "draft_created"
    assert "sha256_hash" in data


def test_duplicate_check():
    res = client.post("/fir/check-duplicate", json={"complaint_text": "Sample test complaint about stolen property."})
    assert res.status_code == 200
    data = res.json()
    assert "is_duplicate" in data
    assert "similarity_score" in data


def test_police_validate_fir():
    payload = {
        "district": "Central",
        "policeStation": "PS001",
        "complainantName": "John Doe",
        "placeAddress": "Station Road",
        "firContents": "The accused broke the store lock and entered unlawfully during night hours.",
        "section1": "303",
    }
    res = client.post("/police/validate-fir", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["status"] == "passed"


def test_police_approve_fir():
    res = client.post("/police/approve-fir", json={"fir_draft_id": "FIR/2026/00099", "officer_name": "Inspector Sharma"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "APPROVED"
    assert "sha256_hash" in data


def test_legal_chat():
    res = client.post("/chat/message", json={"message": "What is the punishment for cheating under BNS?"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "reply" in data
    assert len(data["reply"]) > 20
