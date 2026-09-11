import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates

TEST_INCIDENT = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

sample_queries = [
    TEST_INCIDENT,
    "stolen mobile phone punched by unknown person",
    "voluntarily causing hurt theft mobile phone assault",
    "theft of movable property physical punch hurt"
]

candidate_map = {}
for q in sample_queries:
    res = retrieve(query=q, top_k=20)
    for item in res:
        doc_id = item.get("id")
        if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
            candidate_map[doc_id] = item

cands = list(candidate_map.values())
print(f"Total Unique Candidates Retrieved: {len(cands)}")
for c in cands:
    meta = c.get("metadata", {})
    sec = meta.get("section") or c.get("section")
    title = meta.get("title") or c.get("title")
    print(f"  Sec {sec}: {title} (id: {c.get('id')}, dist: {c.get('distance'):.4f})")

reranked = rerank_candidates(TEST_INCIDENT, cands, top_k=10)
print("\nRERANKED TOP 10:")
for idx, r in enumerate(reranked):
    sec = r.get("section")
    title = r.get("title")
    score = r.get("rerank_score")
    print(f"  {idx+1}. BNS Section {sec} ({title}) - Score: {score:.4f}")
