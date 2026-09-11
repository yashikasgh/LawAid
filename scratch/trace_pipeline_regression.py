import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ai.rag.pipeline import run_pipeline

TEST_INCIDENT = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

print("[1] Executing run_pipeline(TEST_INCIDENT)...")
result = run_pipeline(TEST_INCIDENT)

print("\n--- SANITIZED INCIDENT ---")
print(result.get("sanitized_incident"))

print("\n--- RETRIEVED CANDIDATES (Top Reranked) ---")
retrieved = result.get("retrieved_candidates", [])
for idx, item in enumerate(retrieved[:10]):
    print(f"{idx+1}. BNS Section {item.get('section')} - {item.get('title')} (score: {item.get('rerank_score', 0):.3f})")

print("\n--- GROUNDED ANALYSIS OBJECT ---")
analysis = result.get("analysis", [])
print(json.dumps(analysis, indent=2))
