import json
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import MultiProviderLLMFailoverClient

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    pred_list = json.load(f)

gt_map = {item['id']: item for item in gt_list}
pred_map = {item['id']: item for item in pred_list}

fn_cases = ['T04', 'T08', 'T09', 'T16', 'T18', 'T29']

print("=== FN DETAILED RETRIEVAL DIAGNOSIS ===")

for cid in fn_cases:
    gt = gt_map[cid]
    pred = pred_map[cid]
    incident = gt['incident']
    exp_sup = gt['expected_supported']
    pred_sup = pred['predicted_supported']
    pred_unc = pred['predicted_uncertain']
    
    missing_fns = [s for s in exp_sup if s not in pred_sup]
    
    print(f"\n==========================================")
    print(f"CASE {cid}: Missing FNs: {missing_fns}")
    print(f"Incident: {incident}")
    print(f"Predicted Supported: {pred_sup}")
    print(f"Predicted Uncertain: {pred_unc}")
    
    # 1. NER & Query Gen
    ner_result = extract_entities(incident)
    query_output = generate_queries(ner_result)
    raw_queries = query_output.get("queries", [])
    queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]
    print(f"Generated Queries ({len(queries)}): {queries}")
    
    # 2. Vector Retrieval per query
    all_retrieved_candidates = []
    raw_results_per_query = []
    for q_idx, q_str in enumerate(queries):
        retrieved = retrieve(query=q_str, top_k=20)
        raw_results_per_query.append(retrieved)
        all_retrieved_candidates.extend(retrieved)
        
    # 3. Check raw top-20 for missing sections
    for fn_sec in missing_fns:
        print(f"\n--- Section {fn_sec} Analysis ---")
        found_in_raw = False
        raw_ranks = []
        for q_idx, res_list in enumerate(raw_results_per_query):
            for rank, candidate in enumerate(res_list, start=1):
                sec_num = str(candidate.get('metadata', {}).get('section', ''))
                sec_id = candidate.get('id', '')
                if sec_num == fn_sec or f"bns_{fn_sec}_" in sec_id or f"_{fn_sec}_" in sec_id or sec_id.endswith(f"_{fn_sec}") or sec_id == f"bns_{fn_sec}":
                    found_in_raw = True
                    raw_ranks.append((q_idx + 1, rank, sec_id, round(candidate.get('distance', 0), 4)))
        
        print(f"  Was in raw top-20? {found_in_raw}")
        if found_in_raw:
            print(f"  Raw rank(s) [Query#, Rank, ID, Distance]: {raw_ranks}")
        else:
            print(f"  NOT found in top-20 vector search results for any query.")
            
        # 4. RRF Reranking to Top-15
        reranked = rerank_candidates(all_retrieved_candidates, top_k=15)
        in_top_15 = False
        rrf_rank = None
        for rrf_idx, cand in enumerate(reranked, start=1):
            sec_num = str(cand.get('metadata', {}).get('section', ''))
            sec_id = cand.get('id', '')
            if sec_num == fn_sec or f"bns_{fn_sec}_" in sec_id or f"_{fn_sec}_" in sec_id or sec_id.endswith(f"_{fn_sec}") or sec_id == f"bns_{fn_sec}":
                in_top_15 = True
                rrf_rank = rrf_idx
                break
                
        print(f"  Survived top-15 candidate window? {in_top_15} (RRF Rank: {rrf_rank})")
        if found_in_raw and not in_top_15:
            print(f"  -> LOST DURING RRF TRUNCATION!")
        elif not found_in_raw:
            print(f"  -> RAW RETRIEVAL FAILURE!")
            
        if in_top_15:
            print(f"  Reached legal analyzer!")
            print(f"  Analyzer outcome: In predicted_uncertain? {fn_sec in pred_unc} | In predicted_supported? {fn_sec in pred_sup}")
