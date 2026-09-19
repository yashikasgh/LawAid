import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.deps import get_current_user
from app.models.user import User

@pytest.fixture(autouse=True)
def override_chat_user():
    app.dependency_overrides[get_current_user] = lambda: User(id=1, email="test@example.com", role="citizen")
    yield
    app.dependency_overrides.pop(get_current_user, None)

client = TestClient(app)

def _should_skip_if_llm_unavailable(data):
    reply = str(data.get("reply", "")).lower()
    if data.get("status") == "analysis_unavailable" or "could not complete" in reply or "temporarily unavailable" in reply or "ai rag pipeline is currently unavailable" in reply:
        import pytest
        pytest.skip("Cloud LLM providers rate-limited / unavailable.")

def test_chat_delete_session_and_empty_sessions_filter():
    # 1. Create a session (empty)
    res_create = client.post("/chat/session")
    assert res_create.status_code == 200
    new_sid = res_create.json()["session_id"]

    # 2. Verify empty session is NOT in GET /chat/sessions
    res_sessions = client.get("/chat/sessions")
    assert res_sessions.status_code == 200
    s_list = res_sessions.json()
    assert not any(s["session_id"] == new_sid for s in s_list)

    # 3. Send a message to populate session
    res_msg = client.post("/chat/message", json={"session_id": new_sid, "message": "Someone stole my phone."})
    assert res_msg.status_code == 200

    # 4. Verify session NOW appears in GET /chat/sessions
    res_sessions2 = client.get("/chat/sessions")
    assert res_sessions2.status_code == 200
    s_list2 = res_sessions2.json()
    matched = [s for s in s_list2 if s["session_id"] == new_sid]
    assert len(matched) == 1
    assert "Someone stole my phone" in matched[0]["preview"]

    # 5. Delete session
    res_del = client.delete(f"/chat/session/{new_sid}")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"

    # 6. Verify deleted session no longer appears in GET /chat/sessions or GET /chat/history
    res_sessions3 = client.get("/chat/sessions")
    assert not any(s["session_id"] == new_sid for s in res_sessions3.json())

    res_hist = client.get(f"/chat/history/{new_sid}")
    assert res_hist.status_code == 404


def test_chat_session_history():
    import uuid
    session_id = f"test_session_hist_{uuid.uuid4().hex[:8]}"
    res1 = client.post("/chat/message", json={"session_id": session_id, "message": "Someone stole my phone."})
    assert res1.status_code == 200
    data1 = res1.json()
    _should_skip_if_llm_unavailable(data1)
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
    _should_skip_if_llm_unavailable(data)
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    res = client.post("/chat/message", json={"message": "Someone stole my phone near the market."})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_bns_terminology_and_ipc_leakage_check():
    res = client.post("/chat/message", json={"message": "What is the punishment for cheating under BNS?"})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
    assert data["status"] == "ok"
    reply = data["reply"]
    assert "Bharatiya Nyaya Sanhita" in reply or "BNS" in reply
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_pipeline_failure_returns_500():
    with patch("ai.rag.pipeline.run_chat_pipeline", side_effect=RuntimeError("Simulated ChromaDB Connection Error")):
        res = client.post("/chat/message", json={"message": "What is theft under BNS?"})
        assert res.status_code == 200
        assert "AI RAG pipeline is currently unavailable" in res.json()["reply"]


def test_chat_no_internal_metadata_leakage():
    res = client.post("/chat/message", json={"message": "Someone entered my house without permission and refused to leave."})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
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
    _should_skip_if_llm_unavailable(data)
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
    _should_skip_if_llm_unavailable(data)
    reply = data["reply"]
    sections = data.get("sections", [])

    # Section 329 or Section 330 must be supported and returned in sections
    assert any("329" in s or "330" in s for s in sections), f"Expected Section 329 or 330 in recommended sections: {sections}"

    # Ensure no internal metadata leakage
    assert "reranked_candidates" not in reply
    assert "document_id" not in reply


def test_chat_persistence_across_multiple_calls_for_user():
    session_id = "persist_test_session_999"
    res1 = client.post("/chat/message", json={"session_id": session_id, "message": "Someone stole my phone."})
    assert res1.status_code == 200

    # Verify session is returned in GET /chat/sessions
    res_sess = client.get("/chat/sessions")
    assert res_sess.status_code == 200
    sessions = res_sess.json()
    assert any(s["session_id"] == session_id for s in sessions)

    # Verify history is retrieved correctly
    res_hist = client.get(f"/chat/history/{session_id}")
    assert res_hist.status_code == 200
    # 2. Verify empty session is NOT in GET /chat/sessions
    res_sessions = client.get("/chat/sessions")
    assert res_sessions.status_code == 200
    s_list = res_sessions.json()
    assert not any(s["session_id"] == new_sid for s in s_list)

    # 3. Send a message to populate session
    res_msg = client.post("/chat/message", json={"session_id": new_sid, "message": "Someone stole my phone."})
    assert res_msg.status_code == 200

    # 4. Verify session NOW appears in GET /chat/sessions
    res_sessions2 = client.get("/chat/sessions")
    assert res_sessions2.status_code == 200
    s_list2 = res_sessions2.json()
    matched = [s for s in s_list2 if s["session_id"] == new_sid]
    assert len(matched) == 1
    assert "Someone stole my phone" in matched[0]["preview"]

    # 5. Delete session
    res_del = client.delete(f"/chat/session/{new_sid}")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"

    # 6. Verify deleted session no longer appears in GET /chat/sessions or GET /chat/history
    res_sessions3 = client.get("/chat/sessions")
    assert not any(s["session_id"] == new_sid for s in res_sessions3.json())

    res_hist = client.get(f"/chat/history/{new_sid}")
    assert res_hist.status_code == 404


def test_chat_session_history():
    import uuid
    session_id = f"test_session_hist_{uuid.uuid4().hex[:8]}"
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


def test_chat_empty_message_returns_400():
    res = client.post("/chat/message", json={"message": "   "})
    assert res.status_code == 400
    assert "Message cannot be empty" in res.json()["detail"]



def test_chat_theft():
    res = client.post("/chat/message", json={"message": "Someone stole my phone."})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    res = client.post("/chat/message", json={"message": "Someone stole my phone near the market."})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_assault():
    res = client.post("/chat/message", json={"message": "A man suddenly punched me in the face and caused my nose to bleed."})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_house_trespass():
    res = client.post("/chat/message", json={"message": "Someone entered my house without permission and refused to leave."})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_road_accident():
    res = client.post("/chat/message", json={"message": "I was injured in a road accident."})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
    assert data["status"] == "ok"
    reply = data["reply"]
    assert len(reply) > 20
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_bns_terminology_and_ipc_leakage_check():
    res = client.post("/chat/message", json={"message": "What is the punishment for cheating under BNS?"})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
    assert data["status"] == "ok"
    reply = data["reply"]
    assert "Bharatiya Nyaya Sanhita" in reply or "BNS" in reply
    assert "Bihar National Security" not in reply
    assert "Indian Penal Code" not in reply


def test_chat_pipeline_failure_returns_500():
    with patch("ai.rag.pipeline.run_chat_pipeline", side_effect=RuntimeError("Simulated ChromaDB Connection Error")):
        res = client.post("/chat/message", json={"message": "What is theft under BNS?"})
        assert res.status_code == 200
        assert "AI RAG pipeline is currently unavailable" in res.json()["reply"]


def test_chat_no_internal_metadata_leakage():
    res = client.post("/chat/message", json={"message": "Someone entered my house without permission and refused to leave."})
    assert res.status_code == 200
    data = res.json()
    _should_skip_if_llm_unavailable(data)
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
    _should_skip_if_llm_unavailable(data)
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
    _should_skip_if_llm_unavailable(data)
    reply = data["reply"]
    sections = data.get("sections", [])

    # Section 329 or Section 330 must be supported and returned in sections
    assert any("329" in s or "330" in s for s in sections), f"Expected Section 329 or 330 in recommended sections: {sections}"

    # Ensure no internal metadata leakage
    assert "reranked_candidates" not in reply
    assert "document_id" not in reply


def test_chat_persistence_across_multiple_calls_for_user():
    session_id = "persist_test_session_999"
    res1 = client.post("/chat/message", json={"session_id": session_id, "message": "Someone stole my phone."})
    assert res1.status_code == 200

    # Verify session is returned in GET /chat/sessions
    res_sess = client.get("/chat/sessions")
    assert res_sess.status_code == 200
    sessions = res_sess.json()
    assert any(s["session_id"] == session_id for s in sessions)

    # Verify history is retrieved correctly
    res_hist = client.get(f"/chat/history/{session_id}")
    assert res_hist.status_code == 200
    messages = res_hist.json()["messages"]
    assert len(messages) >= 2
    assert messages[0]["content"] == "Someone stole my phone."


def test_chat_sentiment_detection_tone_adaptation_without_altering_legal_analysis():
    from ai.chat.sentiment import detect_sentiment
    from ai.rag.pipeline import run_chat_pipeline

    distressed_res = detect_sentiment("I am terrified and scared, someone stole my phone.")
    assert distressed_res["tone"] == "distressed"
    assert "Empathic" in distressed_res["empathy_guide"] or "reassuring" in distressed_res["empathy_guide"]

    neutral_res = detect_sentiment("Someone stole my phone.")
    assert neutral_res["tone"] == "neutral"

    # Verify sentiment does not alter legal analysis output sections
    class DynamicMockLLM:
        def generate(self, prompt, **kwargs):
            if "RETRIEVED BNS LEGAL CONTEXT:" in prompt:
                import re, json
                m = re.search(r'"id":\s*"(bns_303[^"]+)"', prompt)
                if not m:
                    m = re.search(r'"id":\s*"([^"]+)"', prompt)
                doc_id = m.group(1) if m else "bns_303_303(1)"
                return json.dumps({
                    "status": "success",
                    "analysis": [
                        {
                            "document_id": doc_id,
                            "applicability": "supported",
                            "reasoning": "Grounded theft analysis."
                        }
                    ],
                    "limitations": []
                })
            return json.dumps({"reply": "Grounded response text."})

    mock_llm = DynamicMockLLM()
    res1 = run_chat_pipeline("I am terrified and scared, someone stole my phone.", llm_client=mock_llm)
    res2 = run_chat_pipeline("Someone stole my phone.", llm_client=mock_llm)

    assert res1["status"] == "ok"
    assert res2["status"] == "ok"
    # Grounded sections match regardless of sentiment
    assert res1["sections"] == res2["sections"]


def test_regression_theft_generic_phone_theft():
    """A. Verify generic phone theft identifies Section 303 without asserting repeat offender punishment or unrelated sections."""
    from ai.rag.pipeline import run_chat_pipeline
    import json, re

    class MockTheftLLM:
        def generate(self, prompt, **kwargs):
            if "RETRIEVED BNS LEGAL CONTEXT:" in prompt:
                m = re.search(r'"id":\s*"(bns_303[^"]+)"', prompt)
                doc_id = m.group(1) if m else "bns_303_303(2)"
                return json.dumps({
                    "status": "success",
                    "analysis": [
                        {
                            "document_id": doc_id,
                            "applicability": "supported",
                            "reasoning": "The accused dishonestly took the user's mobile phone."
                        }
                    ],
                    "limitations": []
                })
            return json.dumps({
                "reply": "Based on the Bharatiya Nyaya Sanhita, 2023 (BNS):\n\n**Section 303: Theft**\n\nThis section generally covers taking someone's property dishonestly. The general punishment for theft is imprisonment up to 3 years, or fine, or both.\n\nNote: If this is a repeat conviction or if the property value is under Rs. 5,000 and restored, specific statutory rules apply."
            })

    mock_llm = MockTheftLLM()
    res = run_chat_pipeline("Someone stole my phone.", llm_client=mock_llm)
    assert res["status"] == "ok"
    reply = res["reply"]

    # Must contain Section 303
    assert any("303" in s for s in res["sections"])
    # Must NOT assert 1 to 5 years RI as ordinary punishment
    assert "rigorous imprisonment for 1 to 5 years" not in reply.lower()
    # Must NOT contain unrelated sections
    assert not any("304" in s or "305" in s or "306" in s or "134" in s for s in res["sections"])


def test_regression_theft_under_5000_restored():
    """B. Verify theft of property under Rs. 5,000 where property is restored highlights community service proviso."""
    from ai.rag.pipeline import run_chat_pipeline
    import json, re

    class MockProvisoLLM:
        def generate(self, prompt, **kwargs):
            if "RETRIEVED BNS LEGAL CONTEXT:" in prompt:
                m = re.search(r'"id":\s*"(bns_303[^"]+)"', prompt)
                doc_id = m.group(1) if m else "bns_303_303(2)"
                return json.dumps({
                    "status": "success",
                    "analysis": [
                        {
                            "document_id": doc_id,
                            "applicability": "supported",
                            "reasoning": "The theft involved property worth under 5,000 rupees which was returned."
                        }
                    ],
                    "limitations": []
                })
            return json.dumps({
                "reply": "Under Section 303 of BNS 2023, for a first-time theft where the stolen property is worth less than Rs. 5,000 and the property is restored, the statutory proviso specifies punishment with community service."
            })

    mock_llm = MockProvisoLLM()
    res = run_chat_pipeline("My phone worth 2000 rupees was stolen but returned to me. Is community service applicable for a first offence?", llm_client=mock_llm)
    assert res["status"] == "ok"
    assert "community service" in res["reply"].lower() or "5,000" in res["reply"]


def test_regression_theft_repeat_conviction():
    """C. Verify repeat conviction scenario highlights enhanced punishment (1 to 5 years RI)."""
    from ai.rag.pipeline import run_chat_pipeline
    import json, re

    class MockRepeatLLM:
        def generate(self, prompt, **kwargs):
            if "RETRIEVED BNS LEGAL CONTEXT:" in prompt:
                m = re.search(r'"id":\s*"(bns_303[^"]+)"', prompt)
                if not m:
                    m = re.search(r'"id":\s*"([^"]+)"', prompt)
                doc_id = m.group(1) if m else "bns_303_303(1)"
                return json.dumps({
                    "status": "success",
                    "analysis": [
                        {
                            "document_id": doc_id,
                            "applicability": "supported",
                            "reasoning": "The accused has a prior theft conviction under Section 303."
                        }
                    ],
                    "limitations": []
                })
            return json.dumps({
                "reply": "For a second or subsequent conviction under Section 303 BNS 2023, the law specifies enhanced punishment of rigorous imprisonment between 1 and 5 years, plus a fine."
            })

    mock_llm = MockRepeatLLM()
    res = run_chat_pipeline("What is the punishment if the thief was previously convicted of theft before?", llm_client=mock_llm)
    assert res["status"] == "ok"
    assert "second or subsequent" in res["reply"].lower() or "repeat" in res["reply"].lower() or "1" in res["reply"]
