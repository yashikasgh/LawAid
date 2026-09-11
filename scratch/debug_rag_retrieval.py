import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.build_retrieval_query import build_retrieval_queries
from ai.rag.retrieval.chroma_retriever import ChromaRetriever
from ai.rag.reranker.reranker import rerank_candidates

INPUT_1 = (
    "On 5 September 2026 at approximately 8:30 PM, I was returning home near the market "
    "when an unknown man suddenly punched me in the face, causing my nose to bleed. "
    "He then took my mobile phone without my consent and ran away on a motorcycle."
)

INPUT_2 = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

def inspect_incident(label, incident):
    print(f"\n=======================================================")
    print(f"INSPECTING: {label}")
    print(f"Text: '{incident}'")
    print(f"=======================================================")
    
    ner = extract_entities(incident)
    print("\n1. NER Extracted Entities:")
    print(json.dumps(ner, indent=2))
    
    queries = build_retrieval_queries(ner, incident)
    print("\n2. Generated Search Queries:")
    for q in queries:
        print(f"  - [{q['type']}] {q['query']}")
        
    retriever = ChromaRetriever()
    candidates = retriever.retrieve(queries, top_k_per_query=20)
    print(f"\n3. Total Unique Candidates Retrieved from Chroma: {len(candidates)}")
    found_303 = any(c.get("section") == "303" for c in candidates)
    found_115 = any(c.get("section") == "115" for c in candidates)
    print(f"   Contains BNS 303 (Theft)? {found_303}")
    print(f"   Contains BNS 115 (Hurt)?  {found_115}")
    
    for c in candidates:
        sec = c.get("section")
        if sec in ["303", "115", "134", "130"]:
            print(f"   -> Retrieved: Section {sec} ({c.get('title')}) | query_type={c.get('matched_query_type')}")
            
    reranked = rerank_candidates(candidates, incident, ner, top_n=5)
    print(f"\n4. Top-5 Reranked Candidates:")
    for r in reranked:
        print(f"   Rank {r.get('rank')}: Section {r.get('section')} - {r.get('title')} (Score: {r.get('rerank_score'):.3f})")

inspect_incident("INPUT 1 (Worked previously)", INPUT_1)
inspect_incident("INPUT 2 (Regression input)", INPUT_2)
