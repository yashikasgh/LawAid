import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
docs_path = PROJECT_ROOT / "ai" / "rag" / "data" / "processed" / "documents.json"

with open(docs_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for d in data:
    if d.get("id") in ["bns_115", "bns_134", "bns_303_303(2)"]:
        print(f"=== ID: {d.get('id')} ===")
        print(f"Metadata: {d.get('metadata')}")
        print(f"Text snippet: {d.get('text')[:300]}\n")
