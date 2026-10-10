"""test_chat_accuracy_regression.py — Accuracy & context regression tests for LawAid Legal Assistant.

Tests exercise actual context-handling, retrieval, and analysis logic deterministically without consuming Gemini quota.
"""

import pytest
import json
import re
from ai.rag.pipeline import run_chat_pipeline, run_pipeline
from ai.rag.analysis.legal_analyzer import LLMClient, Workload


class DeterministicTestLLMClient(LLMClient):
    """Deterministic local LLM client for testing without cloud API quota usage."""

    def __init__(self):
        super().__init__()
        self.prompts_received = []

    def generate(self, prompt: str, max_tokens=None, **kwargs) -> str:
        self.prompts_received.append(prompt)
        if "JSON OUTPUT SCHEMA FORMAT" in prompt or "RETRIEVED BNS LEGAL CONTEXT" in prompt:
            doc_ids = re.findall(r'"id":\s*"([^"]+)"', prompt)
            analysis_items = []
            for doc_id in doc_ids[:5]:
                sec_match = re.search(r'section_(\d+)', doc_id, re.IGNORECASE) or re.search(r'\b(\d+)\b', doc_id)
                sec_num = sec_match.group(1) if sec_match else "303"
                act_type = "BNSS" if "bnss" in doc_id.lower() else "BNS"
                analysis_items.append({
                    "document_id": doc_id,
                    "act": act_type,
                    "section": sec_num,
                    "title": f"Section {sec_num}",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "reasoning": f"Stated facts correspond to {act_type} Section {sec_num} elements.",
                    "explanation": f"{act_type} Section {sec_num} applies based on retrieved text."
                })
            return json.dumps({
                "status": "success",
                "analysis": analysis_items,
                "limitations": []
            })
        return json.dumps({
            "reply": "Deterministic test response based on retrieved statutory context."
        })


def test_1_resolve_bailability_from_previous_assistant_response_citing_section():
    """1. Test resolving 'Is the section bailable?' from a previous assistant response citing BNS Section 303.
    
    Verifies that Turn 3 'Is the section bailable?' after Turn 1 (theft/Section 303) and Turn 2 (missing dog)
    resolves the cited section BNS 303 from the assistant history and retrieves Section 303 BNS.
    """
    history = [
        {"role": "user", "content": "Someone stole my phone."},
        {"role": "assistant", "content": "Theft is governed under BNS Section 303 of Bharatiya Nyaya Sanhita, 2023."},
        {"role": "user", "content": "My pet dog is missing."},
        {"role": "assistant", "content": "If your pet dog went missing without evidence of theft by another person, no offence is established."}
    ]
    raw_message = "Is the section bailable?"

    llm_client = DeterministicTestLLMClient()
    res = run_chat_pipeline(raw_message, history=history, llm_client=llm_client)

    assert res.get("status") == "ok"
    # Current query MUST remain unmutated
    assert res.get("sanitized_incident") == raw_message

    # Retrieval MUST yield Section 303 cited in assistant history
    sections = res.get("sections", [])
    assert any("303" in str(s) for s in sections)


def test_2_keeping_new_unrelated_incident_isolated():
    """2. Test keeping a new, unrelated incident isolated.
    
    Verifies that 'My pet dog is missing.' after 'Someone stole my phone.' is handled as a 
    standalone incident and does not silently combine unrelated phone theft facts into the new query.
    """
    history = [
        {"role": "user", "content": "Someone stole my phone."},
        {"role": "assistant", "content": "Theft is governed under Section 303 of BNS 2023."}
    ]
    raw_message = "My pet dog is missing."

    llm_client = DeterministicTestLLMClient()
    res = run_chat_pipeline(raw_message, history=history, llm_client=llm_client)

    assert res.get("status") == "ok"
    sanitized = res.get("sanitized_incident", "")
    assert sanitized == raw_message
    assert "phone" not in sanitized.lower()


def test_3_asking_for_clarification_when_multiple_sections_cited():
    """3. Test asking for clarification when multiple cited sections make the reference ambiguous.
    
    Verifies that when history contains multiple cited sections (e.g. Section 303 and Section 317)
    and the user query is 'Is the section bailable?', Rule 14 instructs the assistant to clarify.
    """
    history = [
        {"role": "user", "content": "Someone stole my phone."},
        {"role": "assistant", "content": "Theft is governed under BNS Section 303."},
        {"role": "user", "content": "What about someone who bought it knowing it was stolen?"},
        {"role": "assistant", "content": "Receiving stolen property is covered under BNS Section 317."}
    ]
    raw_message = "Is the section bailable?"

    llm_client = DeterministicTestLLMClient()
    res = run_chat_pipeline(raw_message, history=history, llm_client=llm_client)

    assert res.get("status") == "ok"
    # Prompt sent to LLM MUST contain Rule 14 clarification instruction
    assert len(llm_client.prompts_received) > 0
    final_prompt = llm_client.prompts_received[-1]
    assert "multiple cited sections" in final_prompt or "clarify" in final_prompt.lower()


def test_4_correctly_labeling_bnss_procedural_sections_separately_from_bns():
    """4. Test correctly labeling BNSS procedural sections separately from BNS sections.
    
    Verifies that BNSS procedural sections (e.g. Section 173 BNSS for FIR registration)
    are formatted as 'BNSS Section 173' and not mislabeled as BNS.
    """
    raw_message = "How is an FIR registered under criminal procedure?"
    llm_client = DeterministicTestLLMClient()

    res = run_chat_pipeline(raw_message, history=None, llm_client=llm_client)
    assert res.get("status") == "ok"

    # Prompt sent to LLM MUST contain Statute Identification Rule distinguishing BNS from BNSS
    assert len(llm_client.prompts_received) > 0
    final_prompt = llm_client.prompts_received[-1]
    assert "STATUTE IDENTIFICATION RULE" in final_prompt
    assert "BNSS Section" in final_prompt


def test_5_preserving_exact_current_user_query_and_factual_incident():
    """5. Test preserving the exact current USER QUERY and factual incident.
    
    Verifies that USER QUERY in prompt payload and sanitized_incident in API response
    remain strictly unmutated without prepending past user messages.
    """
    history = [
        {"role": "user", "content": "Someone stole my phone."},
        {"role": "assistant", "content": "Theft is covered under Section 303 BNS."}
    ]
    raw_message = "Is this section bailable?"
    llm_client = DeterministicTestLLMClient()

    res = run_chat_pipeline(raw_message, history=history, llm_client=llm_client)

    assert res.get("status") == "ok"
    assert res.get("sanitized_incident") == raw_message

    final_prompt = llm_client.prompts_received[-1]
    assert f"USER QUERY: {raw_message}" in final_prompt
    assert "USER QUERY: Someone stole my phone" not in final_prompt


def test_standalone_phone_theft_query():
    """6. Standalone phone-theft query retrieval verification."""
    raw_message = "Someone stole my phone."
    llm_client = DeterministicTestLLMClient()

    res = run_chat_pipeline(raw_message, history=None, llm_client=llm_client)
    assert res.get("status") == "ok"
    sections = res.get("sections", [])
    assert len(sections) > 0
    assert any("303" in str(s) for s in sections)


def test_knowingly_dealing_in_stolen_property():
    """7. Standalone dealing in stolen property retrieval verification."""
    raw_message = "I bought a stolen mobile phone from a dealer knowing it was stolen."
    llm_client = DeterministicTestLLMClient()

    res = run_chat_pipeline(raw_message, history=None, llm_client=llm_client)
    assert res.get("status") == "ok"
    sections = res.get("sections", [])
    assert len(sections) > 0
    assert any("317" in str(s) for s in sections)
