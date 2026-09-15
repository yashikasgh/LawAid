import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import MultiProviderLLMFailoverClient

gt_path = PROJECT_ROOT / "evaluation" / "ground_truth.json"
preds_path = PROJECT_ROOT / "evaluation" / "predictions.json"

with open(gt_path, "r", encoding="utf-8") as f:
    gt_data = json.load(f)

gt_map = {item["id"]: item for item in gt_data}

target_cases = {
    "T04": ["304"],
    "T08": ["303"],
    "T09": ["304"],
    "T12": ["125"],
    "T16": ["318"],
    "T18": ["316"],
    "T29": ["115", "331"]
}

print("=" * 100)
print("DIAGNOSTIC REPORT FOR RETRIEVAL FAILURE CASES")
print("=" * 100)

llm_client = MultiProviderLLMFailoverClient()

for case_id, missed_secs in target_cases.items():
    case_gt = gt_map[case_id]
    incident_text = case_gt["incident"]
    print(f"\n{"="*50}\nCASE ID: {case_id}\nCategory: {case_gt.get('category')}\nIncident: {incident_text}\nMissed Section(s): {missed_secs}\n{"="*50}")

    # 1. NER
    ner_res = extract_entities(incident_text)
    
    # 2. Query Generation
    q_out = generate_queries(ner_res, llm_client=llm_client)
    raw_queries = q_out.get("queries", [])
    queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]
    if not queries:
        queries = [incident_text]
        
    print(f"\n1. GENERATED QUERIES ({len(queries)} queries):")
    for i, q in enumerate(queries, 1):
        print(f"   [{i}] ({raw_queries[i-1].get('query_type') if i-1 < len(raw_queries) else 'raw'}): {q}")

    # 3. Raw vector retrieval per query
    per_query_retrieval = {}
    all_raw_candidates = {} # doc_id -> list of (query_idx, rank, distance, doc_obj)
    
    for q_idx, q_str in enumerate(queries, 1):
        try:
            ret = retrieve(query=q_str, top_k=20)
            per_query_retrieval[q_idx] = ret
            for item in ret:
                doc_id = item.get("id")
                sec = str(item.get("section", ""))
                if not doc_id:
                    continue
                if doc_id not in all_raw_candidates:
                    all_raw_candidates[doc_id] = []
                all_raw_candidates[doc_id].append({
                    "query_idx": q_idx,
                    "rank": item.get("rank"),
                    "distance": item.get("distance"),
                    "sec": sec,
                    "item": item
                })
        except Exception as e:
            print(f"   Retrieval error for query {q_idx}: {e}")

    # Check if target missed sections appear anywhere in raw retrieval
    print("\n2. RAW RETRIEVAL TARGET CHECK:")
    for target_sec in missed_secs:
        matching_docs = {doc_id: info for doc_id, info in all_raw_candidates.items() if any(i["sec"] == target_sec for i in info)}
        if not matching_docs:
            print(f"   -> Section {target_sec}: NOT RETRIEVED in top-20 of ANY generated query!")
        else:
            print(f"   -> Section {target_sec}: RETRIEVED in raw candidates!")
            for doc_id, info_list in matching_docs.items():
                print(f"      Doc ID: {doc_id}")
                for occ in info_list:
                    print(f"        Query [{occ['query_idx']}] Rank {occ['rank']}, Distance: {occ['distance']:.4f}, Title: {occ['item'].get('title')}")

    # 4. Reranking analysis
    # Flatten candidate_map as done in pipeline
    candidate_map = {}
    for q_idx, ret in per_query_retrieval.items():
        for item in ret:
            doc_id = item.get("id")
            if not doc_id:
                continue
            if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
                candidate_map[doc_id] = item

    raw_candidates_list = list(candidate_map.values())
    reranked = rerank_candidates(
        incident_input=ner_res,
        candidates=raw_candidates_list,
        top_k=None # Get full list to see where they end up
    )

    print("\n3. RERANKING & TRUNCATION CHECK:")
    for target_sec in missed_secs:
        for final_rank, doc in enumerate(reranked, 1):
            sec = str(doc.get("section", ""))
            if sec == target_sec:
                doc_id = doc.get("id")
                score = doc.get("rerank_score")
                print(f"   -> Section {target_sec} ({doc_id}) is RERANKED at Position #{final_rank} (rerank_score: {score:.6f})")
                if final_rank > 10:
                    print(f"      !!! DROPPED BY TOP-10 TRUNCATION !!! (Position {final_rank} > 10)")
                else:
                    print(f"      (Retained in top-10 reranked)")

print("\n" + "=" * 100)
