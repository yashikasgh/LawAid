import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ai.rag.pipeline import run_pipeline, run_chat_pipeline

TEST_MSG = "Someone stole my phone."

print("=== RUNNING PIPELINE ===")
res = run_pipeline(TEST_MSG)
print(json.dumps(res.get("analysis", []), indent=2))

print("\n=== RUNNING CHAT PIPELINE ===")
chat_res = run_chat_pipeline(TEST_MSG)
print(json.dumps(chat_res, indent=2))
