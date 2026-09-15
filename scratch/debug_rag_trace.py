"""debug_rag_trace.py — Step-by-step diagnostic script for LawAid RAG pipeline.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.security.privacy_gateway import sanitize_text
from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.context_builder import build_legal_context
from ai.rag.analysis.legal_analyzer import analyze_incident, GroqLLMClient

DEMO_INCIDENT = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

def run_trace():
    print("=" * 80)
    print("LAWAID RAG DIAGNOSTIC TRACE")
    print("=" * 80)

    # 1. Privacy Gateway
    privacy_res = sanitize_text(DEMO_INCIDENT)
    sanitized_text = privacy_res.get("sanitized_text", "")
    print(f"\n1. SANITIZED INCIDENT TEXT:\n   {sanitized_text}")

    # 2. NER Extraction
    ner_result = extract_entities(sanitized_text)
    print(f"\n2. NER EXTRACTION RESULT:\n   offence_types: {ner_result.get('offence_types')}")
    print(f"   persons: {ner_result.get('persons')}")
    print(f"   locations: {ner_result.get('locations')}")

    # 3. Query Generation (Fallback vs LLM)
    queries_fallback = generate_queries(ner_result, llm_client=None).get("queries", [])
    print(f"\n3a. QUERY GENERATOR (Fallback, llm_client=None):\n   {json.dumps(queries_fallback, indent=2)}")

    queries_llm = []
    try:
        groq_client = GroqLLMClient()
        queries_llm = generate_queries(ner_result, llm_client=groq_client).get("queries", [])
        print(f"\n3b. QUERY GENERATOR (Groq LLM):\n   {json.dumps(queries_llm, indent=2)}")
    except Exception as err:
        print(f"\n3b. QUERY GENERATOR (Groq LLM Error/Rate Limit):\n   {err}")

    # 4. Direct ChromaDB Retrieval Tests
    test_queries = [
        "theft of mobile phone",
        "someone punched me and stole my mobile phone",
        sanitized_text
    ]
    if queries_fallback:
        for q in queries_fallback:
            q_str = q.get("query") if isinstance(q, dict) else str(q)
            if q_str not in test_queries:
                test_queries.append(q_str)
    if queries_llm:
        for q in queries_llm:
            q_str = q.get("query") if isinstance(q, dict) else str(q)
            if q_str not in test_queries:
                test_queries.append(q_str)

    print("\n" + "=" * 80)
    print("4. DIRECT CHROMADB RETRIEVAL TESTS (Top 10 per query)")
    print("=" * 80)

    for query_str in test_queries:
        print(f"\n>>> QUERY: '{query_str}'")
        try:
            results = retrieve(query=query_str, top_k=10)
            print(f"{'Rank':<5} | {'Doc ID':<22} | {'Sec':<5} | {'Clause':<8} | {'Distance':<10} | {'Title'}")
            print("-" * 80)
            for r in results:
                sec_str = str(r.get('section', ''))
                cls_str = r.get('clause') if r.get('clause') else "-"
                dist = r.get('distance', 0.0)
                print(f"{r.get('rank'):<5} | {r.get('id'):<22} | {sec_str:<5} | {cls_str:<8} | {dist:<10.4f} | {r.get('title')}")
        except Exception as err:
            print(f"    Retrieval Error: {err}")

    # 5. Pipeline Deduplication & RRF Reranking Trace
    # Use fallback queries as baseline active queries
    active_queries = [q["query"] for q in queries_fallback if isinstance(q, dict) and "query" in q]
    if not active_queries:
        active_queries = [sanitized_text]

    print("\n" + "=" * 80)
    print("5. PIPELINE DEDUPLICATION & RRF RERANKING TRACE")
    print("=" * 80)

    candidate_map = {}
    for q_str in active_queries:
        try:
            retrieved = retrieve(query=q_str, top_k=20)
            for item in retrieved:
                doc_id = item.get("id")
                if not doc_id:
                    continue
                if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
                    candidate_map[doc_id] = item
        except Exception as err:
            print(f"Retrieval error for query '{q_str}': {err}")

    raw_candidates = list(candidate_map.values())
    print(f"Unique candidates collected before reranking: {len(raw_candidates)}")

    reranked_top_5 = rerank_candidates(
        incident_input=ner_result,
        candidates=raw_candidates,
        top_k=5
    )

    print("\nTOP 5 RERANKED CANDIDATES (passed to Legal Analyzer):")
    print(f"{'Rank':<5} | {'Doc ID':<22} | {'Sec':<5} | {'RRF Score':<12} | {'Distance':<10} | {'Title'}")
    print("-" * 80)
    for idx, cand in enumerate(reranked_top_5):
        print(f"{idx+1:<5} | {cand.get('id'):<22} | {str(cand.get('section')):<5} | {cand.get('rerank_score', 0.0):<12.6f} | {cand.get('distance', 0.0):<10.4f} | {cand.get('title')}")

    # 6. Legal Analyzer / LLM Generation Trace
    print("\n" + "=" * 80)
    print("6. LEGAL ANALYZER / LLM GENERATION TRACE")
    print("=" * 80)

    try:
        groq_client = GroqLLMClient()
        analysis_res = analyze_incident(
            ner_result=ner_result,
            retrieval_result=reranked_top_5,
            llm_client=groq_client
        )
        print(f"STATUS: {analysis_res.get('status')}")
        print(f"ANALYSIS ITEMS ({len(analysis_res.get('analysis', []))}):")
        print(json.dumps(analysis_res.get("analysis"), indent=2))
        print(f"LIMITATIONS:\n{json.dumps(analysis_res.get('limitations'), indent=2)}")
    except Exception as err:
        print(f"LEGAL ANALYZER ERROR / EXCEPTION: {err}")

if __name__ == "__main__":
    run_trace()
