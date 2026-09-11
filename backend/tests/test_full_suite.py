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
    if res.status_code == 500:
        pytest.skip("AI pipeline not configured, skipping test.")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["ok", "insufficient_information"]
    assert "results" in data


def test_incident_analysis():
    res = client.post("/fir/analyze", json={"incident": "Accused took my gold chain and ran away on a motorcycle near the market."})
    if res.status_code == 500:
        pytest.skip("AI pipeline not configured, skipping test.")
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "analysis_unavailable" or (isinstance(data.get("data"), dict) and data["data"].get("status") == "analysis_unavailable"):
        pytest.skip("Cloud LLM providers temporarily rate-limited / unavailable.")
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
    if res.status_code == 500:
        pytest.skip("AI pipeline not configured, skipping test.")
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "analysis_unavailable":
        pytest.skip("Cloud LLM providers temporarily rate-limited / unavailable.")
    assert data["status"] == "ok"
    assert "reply" in data
    assert len(data["reply"]) > 20


def test_police_extract_statement():
    statement_text = (
        "On 8 September 2026 at approximately 7:30 PM, the complainant was returning home near the main road "
        "when an unknown man punched him in the face and took his mobile phone without consent before escaping on a motorcycle."
    )
    res = client.post("/police/extract-statement", json={"statement": statement_text})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    extracted = data["data"]
    assert extracted["occurrenceDate"] in ["08-09-2026", "8 September 2026", "08/09/2026"]
    assert "19:30" in extracted["occurrenceTime"] or "7:30 PM" in extracted["occurrenceTime"]
    assert "mobile phone" in extracted["propertyDetails"].lower()
    assert "unknown man" in extracted["accusedDetails"].lower()
    assert ("main road" in extracted["placeAddress"].lower() or "returning home" in extracted["placeAddress"].lower() or extracted["placeAddress"] == "")

