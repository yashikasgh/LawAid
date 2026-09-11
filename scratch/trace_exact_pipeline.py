import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import _deterministic_legal_analysis_fallback, build_legal_context

DEMO_INCIDENT = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

ner_res = extract_entities(DEMO_INCIDENT)
queries_res = generate_queries(ner_res) # offline deterministic
queries = [q["query"] for q in queries_res.get("queries", [])]

candidate_map = {}
for q in queries:
    res = retrieve(query=q, top_k=20)
    for item in res:
        doc_id = item.get("id")
        if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
            candidate_map[doc_id] = item

raw_candidates = list(candidate_map.values())
reranked = rerank_candidates(DEMO_INCIDENT, raw_candidates, top_k=5)

print("Top 5 Reranked Candidates:")
for idx, r in enumerate(reranked):
    sec = r.get("section") or r.get("metadata", {}).get("section")
    title = r.get("title") or r.get("metadata", {}).get("title")
    print(f"  {idx+1}. Sec {sec}: {title} (id: {r.get('id')}, score: {r.get('rerank_score')})")

context_obj = build_legal_context(ner_res, reranked)
analysis_res = _deterministic_legal_analysis_fallback(context_obj)

print("\nAnalysis Result:")
print(json.dumps(analysis_res, indent=2))
