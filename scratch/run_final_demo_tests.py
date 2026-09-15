"""run_final_demo_tests.py — Limited Real E2E AI Tests for Demo Readiness.

Executes ONLY TWO real API calls:
1. Real Test 1: Citizen Understand Pipeline on Representative Odisha Road-Accident FIR
2. Real Test 2: Police FIR Generation & PDF Rendering
"""

import sys
import json
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai.rag.pipeline import run_pipeline
from ai.fir_engine.fir_ai_generator import generate_structured_fir
from ai.fir_engine.fir_pdf_generator import generate_fir_pdf
from ai.rag.analysis.legal_analyzer import MultiProviderLLMFailoverClient

ROD_ACCIDENT_INCIDENT = (
    "FIRST INFORMATION REPORT. Date: 10/08/2026. Place of occurrence: Near Central Market road. "
    "Complainant states that while he was riding his motorcycle, an unknown motor car driven in a rash "
    "and negligent manner struck the motorcycle from behind. The complainant suffered hurt and bodily injury "
    "on his leg and arm. The driver of the car failed to stop and drove away at high speed."
)

def run_real_tests():
    llm_client = MultiProviderLLMFailoverClient()

    print("=" * 60)
    print("REAL TEST 1 — CITIZEN UNDERSTAND PIPELINE")
    print("=" * 60)
    
    t1_res = run_pipeline(ROD_ACCIDENT_INCIDENT, llm_client=llm_client)
    
    status = t1_res.get("status")
    analysis = t1_res.get("analysis", [])
    limitations = t1_res.get("limitations", [])
    disclaimer = t1_res.get("disclaimer")
    
    print(f"Pipeline Status: {status}")
    print(f"Total Analysis Items Returned: {len(analysis)}")
    
    supported_items = []
    uncertain_items = []
    rejected_items = []
    
    for item in analysis:
        sec = item.get("section")
        clause = item.get("clause", "")
        title = item.get("title")
        app = item.get("applicability")
        reasoning = item.get("reasoning")
        
        info = f"BNS §{sec}{' (' + clause + ')' if clause else ''} — {title}"
        
        if app == "supported":
            supported_items.append((info, reasoning))
        elif app == "uncertain":
            uncertain_items.append((info, reasoning))
        else:
            rejected_items.append((info, reasoning))
            
    print("\n--- SUPPORTED PROVISIONS ---")
    for info, reas in supported_items:
        clean_info = info.encode('ascii', errors='ignore').decode('ascii')
        clean_reas = reas.encode('ascii', errors='ignore').decode('ascii')
        print(f"[SUPPORTED] {clean_info}\n  Reasoning: {clean_reas}\n")

    print("--- UNCERTAIN PROVISIONS ---")
    for info, reas in uncertain_items:
        clean_info = info.encode('ascii', errors='ignore').decode('ascii')
        clean_reas = reas.encode('ascii', errors='ignore').decode('ascii')
        print(f"[UNCERTAIN] {clean_info}\n  Reasoning: {clean_reas}\n")

    print("--- REJECTED / NOT SUPPORTED PROVISIONS ---")
    for info, reas in rejected_items:
        clean_info = info.encode('ascii', errors='ignore').decode('ascii')
        clean_reas = reas.encode('ascii', errors='ignore').decode('ascii')
        print(f"[REJECTED] {clean_info}\n  Reasoning: {clean_reas}\n")
        
    print(f"Disclaimer Present: {bool(disclaimer)}")
    if limitations:
        print(f"Limitations: {limitations}")

    print("\n" + "=" * 60)
    print("REAL TEST 2 — POLICE NEW FIR & PDF GENERATION")
    print("=" * 60)
    
    grounded_analysis_for_fir = [
        {"section": item.get("section"), "clause": item.get("clause"), "title": item.get("title"), "applicability": item.get("applicability")}
        for item in analysis if item.get("applicability") == "supported"
    ]
    
    fir_structured = generate_structured_fir(
        sanitized_incident=ROD_ACCIDENT_INCIDENT,
        grounded_analysis=grounded_analysis_for_fir,
        llm_client=llm_client,
        reference_date=datetime.date(2026, 9, 10)
    )
    
    print("Structured FIR Output:")
    print(f"  District: {fir_structured.get('district')}")
    print(f"  Police Station: {fir_structured.get('police_station')}")
    print(f"  Occurrence Date: {fir_structured.get('occurrence', {}).get('date')} ({fir_structured.get('occurrence', {}).get('day')})")
    print(f"  Occurrence Time: {fir_structured.get('occurrence', {}).get('time')}")
    print(f"  Place of Occurrence: {fir_structured.get('place_of_occurrence', {}).get('address')}")
    print(f"  Property Details: {fir_structured.get('property_details')}")
    print(f"  Accused Details: {fir_structured.get('accused_details')}")
    print(f"  Acts & Sections Emitted: {json.dumps(fir_structured.get('acts_sections'), indent=2)}")
    print(f"  Officer Name: {fir_structured.get('officer', {}).get('name')}")
    
    # PDF Rendering Check
    pdf_bytes = generate_fir_pdf(fir_structured)
    print(f"\nPDF Generated Successfully: {len(pdf_bytes)} bytes rendered")

if __name__ == "__main__":
    run_real_tests()
