import json
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import (
    construct_query_generator_prompt,
    validate_llm_queries,
    _parse_json_from_llm
)
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    pred_list = json.load(f)

gt_map = {item['id']: item for item in gt_list}
pred_map = {item['id']: item for item in pred_list}

print("=== SECTION A & B: METRICS ===")
# Supported exact match and full-set exact match
sup_exact = 0
full_exact = 0

for p in pred_list:
    cid = p['id']
    gt = gt_map[cid]
    exp_sup = set(gt['expected_supported'])
    exp_unc = set(gt['expected_uncertain'])
    pred_sup = set(p['predicted_supported'])
    pred_unc = set(p['predicted_uncertain'])
    
    if pred_sup == exp_sup:
        sup_exact += 1
    if pred_sup == exp_sup and pred_unc == exp_unc:
        full_exact += 1

print(f"Supported Exact Match: {sup_exact} / 30 ({sup_exact/30*100:.2f}%)")
print(f"Full-Set Exact Match: {full_exact} / 30 ({full_exact/30*100:.2f}%)")

print("\n=== SECTION C: QUERY GENERATION AUDIT ===")
query_counts = []
query_type_counts = {}
fallback_count = 0

validation_passed_count = 0

for p in pred_list:
    gen_q = p.get('generated_queries', [])
    query_counts.append(len(gen_q))
    if p.get('fallback_used', False):
        fallback_count += 1
        
    for q_item in gen_q:
        if isinstance(q_item, dict):
            qt = q_item.get('query_type', 'unknown')
            query_type_counts[qt] = query_type_counts.get(qt, 0) + 1

    # Check validation on ner_res
    incident = p['incident']
    ner_res = extract_entities(incident)
    # validate generated_queries structure
    val_out = validate_llm_queries({"queries": gen_q}, ner_res)
    if val_out is not None:
        validation_passed_count += 1
    else:
        print(f"Validation FAILED for case {p['id']}! Gen Qs: {gen_q}")

print(f"Queries per case: {query_counts}")
print(f"Average queries: {sum(query_counts)/len(query_counts):.2f}")
print(f"Min queries: {min(query_counts)}, Max queries: {max(query_counts)}")
print(f"Fallback count: {fallback_count}")
print(f"Query Types Distribution: {query_type_counts}")
print(f"Cases passing production validation: {validation_passed_count} / {len(pred_list)}")

print("\n=== SECTION D: RETRIEVAL DIAGNOSIS FOR REMAINING FNs ===")
fn_cases = []
for p in pred_list:
    cid = p['id']
    gt = gt_map[cid]
    exp_sup = set(gt['expected_supported'])
    pred_sup = set(p['predicted_supported'])
    missing = exp_sup - pred_sup
    if missing:
        fn_cases.append((cid, list(missing)))

print(f"Remaining FN Cases ({len(fn_cases)} cases): {fn_cases}")

for cid, missing_fns in fn_cases:
    gt = gt_map[cid]
    p = pred_map[cid]
    incident = gt['incident']
    gen_q = p.get('generated_queries', [])
    queries = [q['query'] for q in gen_q if isinstance(q, dict) and 'query' in q]
    evidence_ids = p.get('evidence_document_ids', [])
    pred_unc = set(p.get('predicted_uncertain', []))
    pred_sup = set(p.get('predicted_supported', []))
    
    print(f"\nCase {cid} - Missing FNs: {missing_fns}")
    print(f"  Incident: {incident}")
    print(f"  Predicted Supp: {list(pred_sup)} | Predicted Unc: {list(pred_unc)}")
    print(f"  Evidence Doc IDs in Top-15 Pool: {evidence_ids}")
    
    # Run exact retrieval step to get raw ranks per query
    raw_results_per_query = []
    all_retrieved = []
    for q_str in queries:
        retrieved = retrieve(query=q_str, top_k=20)
        raw_results_per_query.append(retrieved)
        all_retrieved.extend(retrieved)
        
    reranked = rerank_candidates(incident, all_retrieved, top_k=15)
    
    for fn_sec in missing_fns:
        found_in_raw = False
        raw_ranks = []
        for q_idx, res_list in enumerate(raw_results_per_query, start=1):
            for r_idx, cand in enumerate(res_list, start=1):
                sec_num = str(cand.get('metadata', {}).get('section', ''))
                sec_id = cand.get('id', '')
                if sec_num == fn_sec or f"bns_{fn_sec}_" in sec_id or f"_{fn_sec}_" in sec_id or sec_id.endswith(f"_{fn_sec}") or sec_id == f"bns_{fn_sec}":
                    found_in_raw = True
                    raw_ranks.append(f"Q{q_idx} Rank #{r_idx} (dist: {round(cand.get('distance',0),4)})")
                    
        in_top15 = any(fn_sec in doc_id or f"_{fn_sec}_" in doc_id or doc_id.endswith(f"_{fn_sec}") for doc_id in evidence_ids)
        rrf_rank = None
        for rrf_idx, cand in enumerate(reranked, start=1):
            sec_num = str(cand.get('metadata', {}).get('section', ''))
            sec_id = cand.get('id', '')
            if sec_num == fn_sec or f"bns_{fn_sec}_" in sec_id or f"_{fn_sec}_" in sec_id or sec_id.endswith(f"_{fn_sec}") or sec_id == f"bns_{fn_sec}":
                rrf_rank = rrf_idx
                break
                
        print(f"  Section {fn_sec}:")
        print(f"    - Raw top-20 retrieved? {found_in_raw} | Raw ranks: {raw_ranks}")
        print(f"    - Survived top-15 pool? {in_top15} | RRF Rank: {rrf_rank}")
        print(f"    - Reached legal analyzer? {in_top15}")
        if in_top15:
            if fn_sec in pred_unc:
                print(f"    - Analyzer decision: UNCERTAIN (marked uncertain instead of supported)")
            else:
                print(f"    - Analyzer decision: REJECTED / NOT_APPLICABLE")
        else:
            print(f"    - Analyzer decision: NOT_REACHED")

