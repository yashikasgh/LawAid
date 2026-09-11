import sys
import json
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.rag.pipeline import run_pipeline

test_incident = (
    "On 10 August 2026, at around 8 PM, near Central Market Road, "
    "an unknown man punched the complainant and stole his mobile phone. The accused is not known"
)

print("=" * 80)
print("RUNNING LAW AID RAG PIPELINE FOR TEST INCIDENT:")
print(f"'{test_incident}'")
print("=" * 80)

res = run_pipeline(raw_incident=test_incident)

print("\n--- PIPELINE RESULT KEYS ---")
print(list(res.keys()))

print("\n--- SANITIZED INCIDENT ---")
print(res.get("sanitized_incident"))

print("\n--- GROUNDED LEGAL ANALYSIS (FULL UNFILTERED CANDIDATE EVALUATIONS) ---")
grounded_analysis = res.get("analysis", [])
print(f"Total evaluated analysis items: {len(grounded_analysis)}")

for idx, item in enumerate(grounded_analysis, 1):
    print(f"\n[Candidate #{idx}]")
    print(f"  Section: {item.get('section')}")
    print(f"  Clause: {item.get('clause')}")
    print(f"  Title: {item.get('title')}")
    print(f"  Offence Type: {item.get('offence_type')}")
    print(f"  Applicability: {item.get('applicability')}")
    print(f"  Reasoning: {item.get('reasoning')}")
    print(f"  Cognizable: {item.get('cognizable')}")
    print(f"  Bailable: {item.get('bailable')}")
    print(f"  Punishment: {item.get('punishment')}")
    evidence = item.get("evidence", [])
    if evidence:
        doc_id = evidence[0].get("document_id")
        rank = evidence[0].get("rank")
        print(f"  Evidence Doc ID: {doc_id} (Retrieval Rank: {rank})")
    else:
        print("  Evidence: None")

print("\n--- LIMITATIONS ---")
print(json.dumps(res.get("limitations", []), indent=2))
