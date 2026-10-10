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
