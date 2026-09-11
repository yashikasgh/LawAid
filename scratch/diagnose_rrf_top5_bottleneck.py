"""diagnose_rrf_top5_bottleneck.py — Deep diagnostic script for RRF Top-5 bottleneck on Section 125.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import MockLLMClient, analyze_incident
import chromadb

FIR_TEXT = (
    "FIRST INFORMATION REPORT. Date: 10/08/2026. Place of occurrence: Near Central Market road. "
    "Complainant states that while he was riding his motorcycle, an unknown motor car driven in a rash "
    "and negligent manner struck the motorcycle from behind. The complainant suffered hurt and bodily injury "
    "on his leg and arm. The driver of the car failed to stop and drove away at high speed."
)

def run_diagnostic():
    print("=" * 60)
    print("1. GENERATING QUERIES FOR ROAD-ACCIDENT FIR")
    print("=" * 60)
    ner_res = extract_entities(FIR_TEXT)
    
    mock_llm_response = json.dumps({
        "queries": [
            {
                "query_type": "fact_focused",
                "query": "motor car driven rashly on public road struck a motorcycle from behind causing leg and arm injuries"
            },
            {
                "query_type": "legal_concept",
                "query": "rash or negligent act endangering human life or personal safety causing hurt"
            },
            {
                "query_type": "action_context",
                "query": "driver hit motorcyclist from behind and fled without stopping"
            },
            {
                "query_type": "incident_context",
                "query": "hit-and-run after striking a motorcycle and causing bodily injury"
            }
        ]
    })
    mock_llm = MockLLMClient(responses=[mock_llm_response])
    query_gen_res = generate_queries(ner_res, llm_client=mock_llm)
    gen_queries = [q["query"] for q in query_gen_res.get("queries", [])]
    print(f"Generated queries ({len(gen_queries)}):")
    for idx, q in enumerate(gen_queries, 1):
        print(f"  Q{idx}: {q}")

    print("\n" + "=" * 60)
    print("2. RAW CANDIDATE POOL BEFORE RRF & PER-QUERY RANKS")
    print("=" * 60)
    
    # Store all per-query retrieval results
    all_query_results = []
    for q_idx, q_str in enumerate(gen_queries, 1):
        ret = retrieve(query=q_str, top_k=20)
        all_query_results.append((q_idx, q_str, ret))

    # Trace how pipeline combines candidates
    # A) Pipeline method (deduplicating in dict first then calling rerank_candidates)
    pipe_candidate_map = {}
    for q_idx, q_str, ret in all_query_results:
        for item in ret:
            doc_id = item.get("id")
            if not doc_id:
                continue
            if doc_id not in pipe_candidate_map or item.get("distance", 1.0) < pipe_candidate_map[doc_id].get("distance", 1.0):
                pipe_candidate_map[doc_id] = item

    pipe_raw_candidates = list(pipe_candidate_map.values())
    pipe_reranked = rerank_candidates(ner_res, pipe_raw_candidates, top_k=10)

    # B) Raw multi-query list method (passing all query results directly to rerank_candidates)
    raw_multi_query_list = []
    for q_idx, q_str, ret in all_query_results:
        for item in ret:
            raw_multi_query_list.append(item)
    
    multi_reranked = rerank_candidates(ner_res, raw_multi_query_list, top_k=10)

    print("\n--- Pipeline RRF Method (Deduplicated before Reranker) Top 10 ---")
    for r_idx, cand in enumerate(pipe_reranked, 1):
        sec = cand.get("section")
        clause = cand.get("clause", "")
        title = cand.get("title")
        score = cand.get("rerank_score")
        dist = cand.get("distance")
        doc_id = cand.get("id")
        
        # Find which queries returned it
        q_ranks = []
        for q_idx, q_str, ret in all_query_results:
            for item in ret:
                if item.get("id") == doc_id:
                    q_ranks.append(f"Q{q_idx}:Rank {item.get('rank')}(dist={item.get('distance'):.4f})")
        
        q_str_repr = ", ".join(q_ranks) if q_ranks else "None"
        print(f"  {r_idx:2d}. {doc_id} | Sec {sec} ({clause}) | RRF Score: {score:.6f} | Best Dist: {dist:.4f}")
        print(f"      Title: {title}")
        print(f"      Returned in: {q_str_repr}")

    print("\n--- Multi-Query Raw List RRF Method (Passed all query lists to Reranker) Top 10 ---")
    for r_idx, cand in enumerate(multi_reranked, 1):
        sec = cand.get("section")
        clause = cand.get("clause", "")
        title = cand.get("title")
        score = cand.get("rerank_score")
        dist = cand.get("distance")
        doc_id = cand.get("id")
        
        q_ranks = []
        for q_idx, q_str, ret in all_query_results:
            for item in ret:
                if item.get("id") == doc_id:
                    q_ranks.append(f"Q{q_idx}:Rank {item.get('rank')}(dist={item.get('distance'):.4f})")
        
        q_str_repr = ", ".join(q_ranks) if q_ranks else "None"
        print(f"  {r_idx:2d}. {doc_id} | Sec {sec} ({clause}) | RRF Score: {score:.6f} | Best Dist: {dist:.4f}")
        print(f"      Title: {title}")
        print(f"      Returned in: {q_str_repr}")

    print("\n" + "=" * 60)
    print("3. SECTION 125 DOCUMENT REPRESENTATION IN CHROMADB")
    print("=" * 60)
    client = chromadb.PersistentClient(path="ai/rag/data/chroma_db")
    coll = client.get_collection("lawaid")
    res_125 = coll.get(where={"section": "125"})
    ids_125 = res_125.get("ids", [])
    metas_125 = res_125.get("metadatas", [])
    docs_125 = res_125.get("documents", [])
    
    print(f"Found {len(ids_125)} document(s) for Section 125 in ChromaDB:")
    for doc_id, meta, doc_text in zip(ids_125, metas_125, docs_125):
        print(f"\n--- Document ID: {doc_id} ---")
        print(f"Metadata: {json.dumps(meta, indent=2)}")
        print("Indexed Text:")
        print(doc_text)
        
        text_lower = doc_text.lower()
        terms_to_check = ["rash", "negligent", "endangering life", "personal safety", "hurt", "grievous hurt"]
        found_terms = {t: (t in text_lower) for t in terms_to_check}
        print(f"Statutory Terms Presence: {json.dumps(found_terms)}")

    print("\n" + "=" * 60)
    print("4. CONTROLLED QUERY COMPARISON FOR NATURAL LANGUAGE VARIANTS")
    print("=" * 60)
    test_queries = [
        ("A", "act endangering life or personal safety of others"),
        ("B", "rash or negligent act endangering life or personal safety"),
        ("C", "rash or negligent act causing hurt to another person"),
        ("D", "negligent act endangering human life and causing bodily hurt"),
        ("E", "act endangering personal safety causing hurt")
    ]
    
    secs_to_track = ["125", "281", "285"]
    
    for label, q_text in test_queries:
        print(f"\nQuery {label}: '{q_text}'")
        ret_results = retrieve(query=q_text, top_k=20)
        
        found_sections = {}
        for item in ret_results:
            sec = str(item.get("section", ""))
            doc_id = item.get("id")
            rank = item.get("rank")
            dist = item.get("distance")
            if sec in secs_to_track or doc_id.startswith("bns_125"):
                if sec not in found_sections:
                    found_sections[sec] = []
                found_sections[sec].append(f"{doc_id} (Rank {rank}, dist={dist:.4f})")
                
        for s in ["125", "281", "285"]:
            if s in found_sections:
                print(f"   * Section {s}: {', '.join(found_sections[s])}")
            else:
                print(f"   * Section {s}: NOT in top 20 retrieval results.")

    print("\n" + "=" * 60)
    print("5. LEGAL RELEVANCE & SEMANTIC OVERLAP FOR RETRIEVED CANDIDATES")
    print("=" * 60)
    false_positives = ["271", "288", "282", "115"]
    for fp_sec in false_positives:
        fp_res = coll.get(where={"section": fp_sec})
        fp_metas = fp_res.get("metadatas", [])
        fp_docs = fp_res.get("documents", [])
        if fp_metas:
            print(f"\n--- Section {fp_sec}: {fp_metas[0].get('title')} ---")
            print(f"Statutory Text Preview:\n{fp_docs[0][:300]}...")
            
    print("\nDiagnostic execution completed.")

if __name__ == "__main__":
    run_diagnostic()
