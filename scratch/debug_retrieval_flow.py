import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates

TEST_INCIDENT = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

ner_res = extract_entities(TEST_INCIDENT)
print("NER Result:")
print(ner_res)

queries_res = generate_queries(ner_res)
queries = [q["query"] for q in queries_res.get("queries", []) if isinstance(q, dict) and "query" in q]
print("\nGenerated Queries:")
for q in queries:
    print(f"  - {q}")

candidate_map = {}
for q_str in queries:
    retrieved = retrieve(query=q_str, top_k=20)
    for item in retrieved:
        doc_id = item.get("id")
        if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
            candidate_map[doc_id] = item

raw_cands = list(candidate_map.values())
print(f"\nTotal Raw Candidates Retrieved: {len(raw_cands)}")
print("\nRaw Retrieved Candidates (with sections):")
for item in raw_cands:
    meta = item.get("metadata", {})
    sec = meta.get("section") or item.get("section")
    title = meta.get("title") or item.get("title")
    dist = item.get("distance")
    print(f"  Sec {sec}: {title} (dist: {dist:.4f}, id: {item.get('id')})")

reranked = rerank_candidates(TEST_INCIDENT, raw_cands, top_k=10)
print("\nReranked Top 10:")
for idx, item in enumerate(reranked):
    sec = item.get("section")
    title = item.get("title")
    score = item.get("rerank_score")
    print(f"  {idx+1}. Sec {sec}: {title} (score: {score:.4f}, dist: {item.get('distance'):.4f})")
