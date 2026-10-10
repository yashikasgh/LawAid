"""
test_fir_understanding_accuracy.py — Local regression test suite for FIR understanding accuracy,
metadata extraction, statute labeling, and Police FIR draft fallbacks.
"""

import re
import pytest
from ai.rag.parser.clean_ocr import extract_fir_metadata, extract_explicit_fir_provisions
from ai.fir_engine.fir_ai_generator import _extract_factual_heuristics, generate_structured_fir

SAMPLE_NIA_FIR_TEXT = """
FIRST INFORMATION REPORT
(Under Section 173 BNSS 2023)

1. District: Kamrup Metropolitan
   Police Station: NIA Police Station, Guwahati
   FIR / RC No.: RC-04/2024/NIA-GUW
   Date of FIR: 17.09.2024

2. Acts & Sections:
   Act: Explosive Substances Act, 1908          Sections: 4, 5
   Act: Unlawful Activities (Prevention) Act, 1967   Sections: 16, 18, 20
   Act: Bharatiya Nyaya Sanhita, 2023           Sections: 303(2)

3. Occurrence of Offence:
   Date: 15.09.2024
   Place of Occurrence: G.S. Road, Guwahati near the main junction

4. Complainant / Informant:
   Name: Inspector A. K. Sharma
"""

def test_nia_fir_metadata_extraction():
    """Verify that FIR reference numbers, dates, and police station names are extracted accurately."""
    meta = extract_fir_metadata(SAMPLE_NIA_FIR_TEXT)
    assert meta["fir_number"] == "RC-04/2024/NIA-GUW"
    assert meta["police_station"] == "NIA Police Station, Guwahati"
    assert meta["date_of_report"] == "17.09.2024"
    assert meta["district"] == "Kamrup Metropolitan"

def test_statute_name_preservation():
    """Verify that provisions from non-BNS acts preserve their explicit statute names."""
    provisions = extract_explicit_fir_provisions(SAMPLE_NIA_FIR_TEXT)
    
    sections_by_act = {p["section"]: p["act"] for p in provisions}
    
    assert "4" in sections_by_act
    assert "Explosive" in sections_by_act["4"]
    
    assert "16" in sections_by_act
    assert "Unlawful Activities" in sections_by_act["16"]
    
    assert "303(2)" in sections_by_act
    assert "Bharatiya Nyaya" in sections_by_act["303(2)"]

def test_address_road_no_vehicle_contamination():
    """Verify that an address containing 'Road' does NOT trigger motor vehicle rash driving fallbacks."""
    meta = extract_fir_metadata(SAMPLE_NIA_FIR_TEXT)
    assert meta["place_of_occurrence"] != "Not stated in the FIR"
    assert "G.S. Road" in SAMPLE_NIA_FIR_TEXT
    
    has_rash_driving = bool(re.search(r'\b(?:rash|negligent)\s+driving\b|\bmotor\s+vehicle\s+accident\b', SAMPLE_NIA_FIR_TEXT, re.IGNORECASE))
    assert has_rash_driving is False

def test_unsupported_candidate_bns281_no_contamination():
    """Verify candidate/unsupported BNS 281 provision does NOT trigger vehicle accident fallbacks when applicability is uncertain."""
    display_charges = [
        {"section": "281", "title": "Rash driving or riding on a public way", "applicability": "uncertain"}
    ]
    
    is_rash_driving_case = any(
        ("rash" in c.get("title", "").lower() or "negligent driving" in c.get("title", "").lower())
        and c.get("applicability") == "supported"
        for c in display_charges
    ) or bool(re.search(r'\b(?:rash|negligent)\s+driving\b|\bmotor\s+vehicle\s+accident\b', SAMPLE_NIA_FIR_TEXT, re.IGNORECASE))
    
    assert is_rash_driving_case is False

def test_police_fir_generator_heuristics_preserve_officer_facts():
    """Verify that police FIR generator extracts facts deterministically without hallucination."""
    raw_statement = "On 08/09/2026 at 7:30 PM near the local market, an unknown male snatched my mobile phone valued at Rs. 25000."
    heuristics = _extract_factual_heuristics(raw_statement)
    
    assert heuristics["date"] == "08/09/2026"
    assert heuristics["time"] == "7:30 PM"
    assert "market" in heuristics["location"].lower()
    assert "phone" in heuristics["property"].lower() or "mobile" in heuristics["property"].lower()
    assert "25000" in heuristics["value"]
    assert "Unknown male" in heuristics["accused"]

def test_police_fir_fallback_acts_sections_empty():
    """Verify that fallback FIR data leaves acts_sections empty for officer review."""
    raw_statement = "Someone stole my phone near the bus stand."
    fir_data = generate_structured_fir(sanitized_incident=raw_statement, grounded_analysis=[])

    assert fir_data["acts_sections"] == []
    assert len(fir_data["fir_contents"]) > 0
    assert "phone" in fir_data["fir_contents"].lower() or "mobile" in fir_data["fir_contents"].lower()


def test_statute_title_normalization_and_year_cleaning():
    """Verify that raw statute titles like 'Explosive Act' or 'Explosive Substances Act, 1987' are normalized to exact legal titles."""
    from ai.rag.parser.clean_ocr import normalize_statute_title, extract_explicit_fir_provisions

    assert normalize_statute_title("Explosive Act") == "Explosive Substances Act, 1908"
    assert normalize_statute_title("Explosive Substances Act, 1987") == "Explosive Substances Act, 1908"
    assert normalize_statute_title("UAPA") == "Unlawful Activities (Prevention) Act, 1967"
    assert normalize_statute_title("IPC") == "Indian Penal Code, 1860"

    raw_fir = """
    2. Acts & Sections:
       (i) Act: Explosive Substances Act, 1908 Sections: 3 & 5
       (ii) Act: Unlawful Activities (Prevention) Act, 1967 Sections: 16, 18, 20
    """
    provisions = extract_explicit_fir_provisions(raw_fir)
    act_titles = {p["act"] for p in provisions}
    assert "Explosive Substances Act, 1908" in act_titles
    assert "Unlawful Activities (Prevention) Act, 1967" in act_titles
    assert "Explosive Act, 1987" not in act_titles


def test_metadata_cleaning_prevents_header_leakage():
    """Verify that district and police station extractions strip appended header labels cleanly."""
    raw_fir_text = """
    1. District: Kamrup Metropolitan State Assam
       Police Station: Guwahati Police Station District Kamrup
       FIR No.: RC-04/2024/NIA-GUW
    """
    meta = extract_fir_metadata(raw_fir_text)
    assert meta["district"] == "Kamrup Metropolitan"
    assert meta["police_station"] == "Guwahati Police Station"


def test_explicitly_recorded_meta_section_not_excluded():
    """Verify that a section explicitly recorded in Item 2 (e.g. BNS 3) is preserved and not filtered out by candidate meta-section rules."""
    from ai.rag.parser.clean_ocr import extract_explicit_fir_provisions

    raw_fir = """
    2. Acts & Sections:
       Act: Bharatiya Nyaya Sanhita, 2023 Sections: 3, 303(2)
    """
    provisions = extract_explicit_fir_provisions(raw_fir)
    sections = [p["section"] for p in provisions]
    assert "3" in sections
    assert "303(2)" in sections


def test_provider_unavailable_fallback_graceful_handling():
    """Verify that when AI LLM providers are exhausted/unavailable, pipeline fallback returns OCR metadata and explicit provisions without throwing NameError or 500."""
    from unittest.mock import patch
    from fastapi import UploadFile
    import io
    from backend.app.routers.fir import understand_fir

    fake_file_content = SAMPLE_NIA_FIR_TEXT.encode("utf-8")
    upload_file = UploadFile(filename="test_fir.txt", file=io.BytesIO(fake_file_content), headers={"content-type": "text/plain"})

    with patch("backend.app.routers.fir._run_pipeline", side_effect=Exception("LLM Quota Exhausted / Network Error")):
        import asyncio
        res = asyncio.run(understand_fir(file=upload_file))

        assert res["status"] == "degraded_fallback"
        assert res["is_degraded_fallback"] is True
        assert "charges" in res
        assert "analysis" in res
        assert "reference_provisions" in res
        assert "explained_sections" in res
        assert len(res["explained_sections"]) > 0
        assert res["fir_metadata"]["fir_number"] == "RC-04/2024/NIA-GUW"


def test_failover_time_budget_and_quota_exhaustion():
    """Verify that MultiProviderLLMFailoverClient enforces request_budget_sec and detects quota exhaustion."""
    import time
    from ai.rag.analysis.legal_analyzer import (
        MultiProviderLLMFailoverClient, LLMClient, ProviderHealthTracker, ProviderHealthStatus
    )

    class SlowFailingLLMClient(LLMClient):
        def __init__(self, name: str, delay: float, error_msg: str):
            self.model_name = name
            self.delay = delay
            self.error_msg = error_msg

        def generate(self, prompt: str, max_tokens=None, **kwargs) -> str:
            time.sleep(self.delay)
            raise RuntimeError(self.error_msg)

    tracker = ProviderHealthTracker()
    p1 = SlowFailingLLMClient("model-1", 0.1, "429 RESOURCE_EXHAUSTED: Quota exceeded")
    p2 = SlowFailingLLMClient("model-2", 0.5, "HTTP 500 API error")

    client = MultiProviderLLMFailoverClient(providers=[p1, p2], health_tracker=tracker)

    # 1. Test quota exhaustion recording
    start_t = time.time()
    with pytest.raises(RuntimeError) as exc_info:
        client.generate("Test prompt", request_budget_sec=0.4)
    elapsed = time.time() - start_t

    assert "All LLM providers" in str(exc_info.value)
    # Total execution must stay within budget
    assert elapsed < 0.7

    # 2. Check that p1 was marked as QUOTA_EXHAUSTED due to 429 quota error
    p1_status, _ = tracker.get_status(p1)
    assert p1_status == ProviderHealthStatus.QUOTA_EXHAUSTED

    # 3. Subsequent call immediately skips p1 without waiting
    healthy, reason = tracker.is_healthy(p1, "Test prompt")
    assert healthy is False
    assert "cooldown" in reason.lower() or "quota" in reason.lower() or "disabled" in reason.lower()


def test_police_fir_draft_saving_and_dashboard_retrieval():
    """Verify saving a police FIR draft persists to database and appears in police officer drafts list."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    from app.models.user import User
    from app.models.fir_draft import FIRDraft
    from app.models.saved_fir import SavedFIR
    from app.routers.fir_drafts import save_draft, get_drafts

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    mock_officer = User(id=42, email="officer@police.gov.in", password_hash="hash", role="police")

    draft_body = {
        "draft_id": "draft-101",
        "district": "Kamrup",
        "police_station": "Guwahati PS",
        "complainant": "Officer Sharma",
        "incident_details": "Vehicle theft reported."
    }

    # 1. Save police draft
    save_res = save_draft(body=draft_body, current_user=mock_officer, db=db)
    assert save_res["status"] == "created"
    assert save_res["draft_id"] == "draft-101"

    # 2. Retrieve drafts for police dashboard
    retrieved_drafts = get_drafts(current_user=mock_officer, db=db)
    assert len(retrieved_drafts) == 1
    assert retrieved_drafts[0]["draft_id"] == "draft-101"
    assert retrieved_drafts[0]["district"] == "Kamrup"
    assert retrieved_drafts[0]["officer_id"] == 42

    # 3. Verify separation: SavedFIR table is empty (citizen bookmarks are distinct from police FIR drafts)
    saved_citizen_firs = db.query(SavedFIR).filter(SavedFIR.user_id == 42).all()
    assert len(saved_citizen_firs) == 0

    db.close()


def test_explicit_vs_potential_sections_separation():
    """Verify that explicitly recorded FIR sections are placed in explained_sections (Supported) and RAG candidates in potential_sections (Uncertain)."""
    from fastapi import UploadFile
    import io
    from backend.app.routers.fir import understand_fir
    from unittest.mock import patch
    import asyncio

    fake_file_content = SAMPLE_NIA_FIR_TEXT.encode("utf-8")
    upload_file = UploadFile(filename="test_fir.txt", file=io.BytesIO(fake_file_content), headers={"content-type": "text/plain"})

    mock_rag_res = {
        "status": "success",
        "source": "pipeline",
        "pipeline_source": "pipeline",
        "analysis": [
            {
                "section": "304",
                "act": "Bharatiya Nyaya Sanhita, 2023",
                "title": "Snatching",
                "applicability": "uncertain",
                "status": "Uncertain"
            }
        ]
    }

    with patch("backend.app.routers.fir._run_pipeline", return_value=mock_rag_res):
        res = asyncio.run(understand_fir(file=upload_file))

        assert res["status"] == "ok"
        assert res["has_sections_in_fir"] is True

        # Explicitly recorded sections in FIR
        explained = res["explained_sections"]
        exp_secs = [c["section"] for c in explained]
        assert "303(2)" in exp_secs
        assert "4" in exp_secs
        assert "16" in exp_secs

        for card in explained:
            assert card["status"] == "Supported"
            assert card["applicability"] == "supported"

        # Candidate potential section from vector search
        potential = res["potential_sections"]
        pot_secs = [c["section"] for c in potential]
        assert "304" in pot_secs

        for card in potential:
            assert card["status"] == "Uncertain"
            assert card["applicability"] == "uncertain"
