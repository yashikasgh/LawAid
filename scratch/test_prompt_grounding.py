import sys
import json
from pathlib import Path

# Ensure project root and backend are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai.rag.pipeline import run_pipeline
from ai.rag.analysis.legal_analyzer import MultiProviderLLMFailoverClient

incidents = [
    ("Incident A (No value stated)", "On 10 August 2026, at around 8 PM, near Central Market Road, an unknown man punched the complainant and stole his mobile phone. The accused is not known"),
    ("Incident B (Valued < 5,000)", "An unknown man stole the complainant's mobile phone worth 3,000 rupees from his pocket."),
    ("Incident C (Explicit force for theft)", "An unknown man punched the complainant in the face in order to snatch his mobile phone from his hand and ran away.")
]

llm = MultiProviderLLMFailoverClient()

for title, text in incidents:
    print("\n" + "=" * 80)
    print(f"TESTING: {title}")
    print(f"Text: '{text}'")
    print("=" * 80)

    res = run_pipeline(raw_incident=text, llm_client=llm)
    analysis = res.get("analysis", [])

    print(f"Total analysis items: {len(analysis)}")
    for item in analysis:
        sec = item.get("section")
        cl = item.get("clause")
        t = item.get("title")
        app = item.get("applicability")
        reason = item.get("reasoning")
        off = item.get("offence_type")
        cog = item.get("cognizable")
        print(f"  Sec {sec} ({cl}) [{t}] -> Applicability: {app}")
        print(f"    Offence: {off} | Cognizable: {cog}")
        print(f"    Reasoning: {reason}")
