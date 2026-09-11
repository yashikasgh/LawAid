import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ai.security.privacy_gateway import sanitize_text
from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import _deterministic_legal_analysis_fallback, build_legal_context

DEMO_INCIDENT = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

privacy_res = sanitize_text(DEMO_INCIDENT)
sanitized_text = privacy_res.get("sanitized_text", "")
ner_result = extract_entities(sanitized_text)

print("NER Result:")
print(json.dumps(ner_result, indent=2))

query_output = generate_queries(ner_result)
raw_queries = query_output.get("queries", [])
queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]

print("\nGenerated Queries:")
for q in queries:
    print(f"  - {q}")

candidate_map = {}
for q_str in queries:
    retrieved = retrieve(query=q_str, top_k=20)
    for item in retrieved:
        doc_id = item.get("id")
        if not doc_id:
            continue
        if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
            candidate_map[doc_id] = item

raw_candidates = list(candidate_map.values())
print(f"\nTotal Raw Candidates: {len(raw_candidates)}")
for c in raw_candidates:
    sec = c.get("section") or c.get("metadata", {}).get("section")
    if str(sec) in ["115", "303", "134", "130"]:
        print(f"  Sec {sec}: {c.get('title')} (id: {c.get('id')}, dist: {c.get('distance'):.4f})")

reranked = rerank_candidates(incident_input=ner_result, candidates=raw_candidates, top_k=10)
print("\nReranked Top 10:")
for idx, r in enumerate(reranked):
    sec = r.get("section") or r.get("metadata", {}).get("section")
    print(f"  {idx+1}. Sec {sec}: {r.get('title')} (id: {r.get('id')}, score: {r.get('rerank_score'):.4f}, dist: {r.get('distance'):.4f})")
