import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_empty_message_returns_400():
    res = client.post("/chat/message", json={"message": "   "})
    assert res.status_code == 400
    assert "Message cannot be empty" in res.json()["detail"]


def test_chat_session_history():
    session_id = "test_session_123"
    res1 = client.post("/chat/message", json={"session_id": session_id, "message": "Someone stole my phone."})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "ok"
    assert data1["session_id"] == session_id
    assert len(data1["reply"]) > 10

    res_hist = client.get(f"/chat/history/{session_id}")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert hist_data["session_id"] == session_id
    messages = hist_data["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Someone stole my phone."
    assert messages[1]["role"] == "assistant"
    assert len(messages[1]["content"]) > 0


def test_chat_theft():
    res = client.post("/chat/message", json={"message": "Someone stole my phone."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    res = client.post("/chat/message", json={"message": "Someone stole my phone near the market."})
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "analysis_unavailable" or "temporarily unavailable" in data.get("reply", "").lower():
        import pytest
        pytest.skip("Cloud LLM providers rate-limited / unavailable.")
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_assault():
    res = client.post("/chat/message", json={"message": "A man suddenly punched me in the face and caused my nose to bleed."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_house_trespass():
    res = client.post("/chat/message", json={"message": "Someone entered my house without permission and refused to leave."})
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "analysis_unavailable" or "temporarily unavailable" in data.get("reply", "").lower():
        import pytest
        pytest.skip("Cloud LLM providers rate-limited / unavailable.")
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_road_accident():
    res = client.post("/chat/message", json={"message": "I was injured in a road accident."})
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "analysis_unavailable" or "temporarily unavailable" in data.get("reply", "").lower():
        import pytest
        pytest.skip("Cloud LLM providers rate-limited / unavailable.")
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_bns_terminology_and_ipc_leakage_check():
    res = client.post("/chat/message", json={"message": "What is the punishment for cheating under BNS?"})
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "analysis_unavailable" or "temporarily unavailable" in data.get("reply", "").lower():
        import pytest
        pytest.skip("Cloud LLM providers rate-limited / unavailable.")
    assert data["status"] == "ok"
    reply = data["reply"]
    assert "Bharatiya Nyaya Sanhita" in reply or "BNS" in reply
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_pipeline_failure_returns_500():
    with patch("ai.rag.pipeline.run_chat_pipeline", side_effect=RuntimeError("Simulated ChromaDB Connection Error")):
        res = client.post("/chat/message", json={"message": "What is theft under BNS?"})
        assert res.status_code == 500
        assert "Legal Chat RAG Pipeline Error" in res.json()["detail"]


def test_chat_no_internal_metadata_leakage():
    res = client.post("/chat/message", json={"message": "Someone entered my house without permission and refused to leave."})
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "analysis_unavailable" or "temporarily unavailable" in data.get("reply", "").lower():
        import pytest
        pytest.skip("Cloud LLM providers rate-limited / unavailable.")
    reply = data["reply"]
    sections = data.get("sections", [])

    # Ensure reply contains no internal implementation labels or raw IDs
    assert "reranked_candidates" not in reply
    assert "document_id" not in reply
    assert "candidate_id" not in reply
    assert "vector distance" not in reply.lower()
    assert "rerank_score" not in reply

    # Ensure section titles returned in API sections list are clean
    for s in sections:
        assert "reranked_candidates" not in s
        assert "document_id" not in s


def test_chat_theft_grounding_and_no_affirmative_314_recommendation():
    res = client.post("/chat/message", json={"message": "Someone stole my phone."})
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "analysis_unavailable" or "temporarily unavailable" in data.get("reply", "").lower():
        import pytest
        pytest.skip("Cloud LLM providers rate-limited / unavailable.")
    reply = data["reply"]
    sections = data.get("sections", [])

    # Section 303 must be supported and returned in sections
    assert any("303" in s for s in sections), f"Expected Section 303 in recommended sections: {sections}"
    
    # Section 314 must NOT be in recommended sections list for simple theft
    assert not any("314" in s for s in sections), f"Section 314 should NOT be in recommended sections: {sections}"

    # Ensure Section 314 is not affirmatively recommended to register in reply text
    lower_reply = reply.lower()
    assert "register a case under section 314" not in lower_reply
    assert "register under sections 303 and 314" not in lower_reply
    assert "register under section 314" not in lower_reply

    # Ensure no internal metadata leakage
    assert "reranked_candidates" not in reply
    assert "document_id" not in reply


def test_chat_house_trespass_grounding():
    res = client.post("/chat/message", json={"message": "Someone entered my house without permission and refused to leave."})
    assert res.status_code == 200
    data = res.json()
    if data.get("status") == "analysis_unavailable" or "temporarily unavailable" in data.get("reply", "").lower():
        import pytest
        pytest.skip("Cloud LLM providers rate-limited / unavailable.")
    reply = data["reply"]
    sections = data.get("sections", [])

    # Section 329 or Section 330 must be supported and returned in sections
    assert any("329" in s or "330" in s for s in sections), f"Expected Section 329 or 330 in recommended sections: {sections}"

    # Ensure no internal metadata leakage
    assert "reranked_candidates" not in reply
    assert "document_id" not in reply


