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

test_incident = (
    "On 10 August 2026, at around 8 PM, near Central Market Road, "
    "an unknown man punched the complainant and stole his mobile phone. The accused is not known"
)

res = run_pipeline(raw_incident=test_incident)

print("=" * 80)
print("RAW GROUNDED LEGAL ANALYSIS OUTPUT FOR TEST INCIDENT:")
print("=" * 80)
print(json.dumps(res.get("analysis", []), indent=2))
