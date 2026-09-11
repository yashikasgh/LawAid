import os
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

INCIDENT_2 = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

ner = extract_entities(INCIDENT_2)
print("NER Entities:", ner)

# Generate queries
q_output = generate_queries(ner)
print("Generated Queries:", q_output)

queries = [q["query"] for q in q_output.get("queries", []) if isinstance(q, dict) and "query" in q]
if not queries:
    queries = [INCIDENT_2]

print(f"\nExecuting ChromaDB retrieve() for {len(queries)} queries...")

candidate_map = {}
for q in queries:
    res = retrieve(q, top_k=20)
    print(f"\nQuery: '{q}' -> Retrieved {len(res)} results:")
    for r in res:
        sec = r.get("section")
        doc_id = r.get("id")
        if doc_id not in candidate_map or r.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
            candidate_map[doc_id] = r
        print(f"   Sec {sec}: {r.get('title')} (dist: {r.get('distance'):.4f})")

all_candidates = list(candidate_map.values())
print(f"\nTotal unique candidates: {len(all_candidates)}")

has_303 = any(str(c.get("section")) == "303" for c in all_candidates)
has_115 = any(str(c.get("section")) == "115" for c in all_candidates)

print(f"Contains Section 303 in Chroma retrieved candidates? {has_303}")
print(f"Contains Section 115 in Chroma retrieved candidates? {has_115}")

reranked = rerank_candidates(INCIDENT_2, all_candidates, top_k=10)
print("\nTop 10 Reranked Candidates:")
for idx, r in enumerate(reranked):
    print(f"  {idx+1}. Sec {r.get('section')}: {r.get('title')} (score: {r.get('rerank_score'):.4f})")
