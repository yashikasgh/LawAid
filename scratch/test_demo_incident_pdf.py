import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ai.rag.pipeline import run_pipeline
from ai.fir_engine.fir_ai_generator import generate_structured_fir
from ai.fir_engine.fir_pdf_generator import generate_fir_pdf

DEMO_INCIDENT = (
    "On 8 September 2026 at approximately 7:30 PM, the complainant was returning home from the local market "
    "when an unknown man approached him near the main road. The man suddenly punched the complainant in the face, "
    "causing a bleeding injury to his nose. During the incident, the accused took the complainant's mobile phone "
    "without his consent and immediately fled from the scene on a motorcycle. The complainant requests that "
    "appropriate legal action be taken and that the accused be identified and traced."
)

print("[1] Running RAG legal analysis pipeline...")
rag_result = run_pipeline(DEMO_INCIDENT)

analysis = rag_result.get("analysis", [])
print(f"Grounded analysis retrieved {len(analysis)} provisions.")

supported_provisions = []
for item in analysis:
    print(f"  - Section {item.get('section')}: {item.get('title')} -> {item.get('applicability')}")
    if item.get("applicability") == "supported":
        supported_provisions.append(item)

print("\n[2] Generating Structured IF1 FIR JSON...")
fir_json = generate_structured_fir(
    sanitized_incident=rag_result.get("sanitized_incident", DEMO_INCIDENT),
    grounded_analysis=analysis
)

print("\nSTRUCTURED FIR JSON RESULT:")
print(json.dumps(fir_json, indent=2))

print("\n[3] Overlaying onto Official IF1 PDF Template...")
pdf_bytes = generate_fir_pdf(fir_json)

out_pdf_path = PROJECT_ROOT / "scratch" / "test_output_demo_fir.pdf"
with open(out_pdf_path, "wb") as f:
    f.write(pdf_bytes)

print(f"\nSUCCESS: Generated PDF saved to {out_pdf_path} (Size: {len(pdf_bytes)} bytes)")
