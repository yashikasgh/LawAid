import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
RETRIEVAL_DIR = PROJECT_ROOT / "ai" / "rag" / "retrieval"
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ai.security.privacy_gateway import sanitize_text
from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates, _extract_incident_facts
from ai.rag.analysis.legal_analyzer import analyze_incident, GroqLLMClient

def trace_incident(incident_text: str):
    print(f"\n=======================================================")
    print(f"INCIDENT: '{incident_text}'")
    print(f"=======================================================")
    
    # 1. Privacy & NER
    sanitized = sanitize_text(incident_text).get("sanitized_text", "")
    ner_res = extract_entities(sanitized)
    facts = _extract_incident_facts(sanitized)
    print("\n1. NER & FACT EXTRACTION:")
    print("   Raw Offence Types:", ner_res.get("offence_types", []))
    print("   Extracted Fact Flags:", [k for k, v in facts.items() if v])
    
    # 2. Query Generation
    llm_client = GroqLLMClient()
    query_output = generate_queries(ner_res, llm_client=llm_client)
    raw_queries = query_output.get("queries", [])
    queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]
    if not queries:
        queries = [sanitized]
    print("\n2. GENERATED QUERIES:")
    for q in queries:
        print("   -", q)
        
    # 3. ChromaDB Retrieval
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
    print(f"\n3. CHROMADB RETRIEVAL: {len(raw_candidates)} total unique candidates retrieved across queries.")
    print("   Top-10 Raw Retrieval Candidates (by distance):")
    sorted_raw = sorted(raw_candidates, key=lambda x: x.get("distance", 1.0))
    for c in sorted_raw[:10]:
        print(f"     Sec {c.get('section')}: {c.get('title')} (dist: {c.get('distance'):.4f})")
        
    # 4. Reranking
    top5 = rerank_candidates(incident_input=ner_res, candidates=raw_candidates, top_k=5)
    print("\n4. RERANKED TOP-5 CANDIDATES:")
    for c in top5:
        print(f"     Sec {c.get('section')}: {c.get('title')} (score: {c.get('rerank_score')})")
        
    # 5. LLM Grounded Legal Analysis
    analysis_result = analyze_incident(ner_result=ner_res, retrieval_result=top5, llm_client=llm_client)
    print("\n5. GROUNDED LEGAL ANALYSIS:")
    for a in analysis_result.get("analysis", []):
        print(f"     Sec {a.get('section')} ({a.get('offence_type')}): {a.get('applicability')} -> {a.get('reasoning')}")

if __name__ == "__main__":
    incidents = [
        "Someone entered my house without permission and refused to leave.",
        "I was injured in a road accident."
    ]
    for inc in incidents:
        trace_incident(inc)
