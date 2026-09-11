import json
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    pred_list = json.load(f)

gt_map = {item['id']: item for item in gt_list}
pred_map = {item['id']: item for item in pred_list}

print("==================================================================")
print("SECTION C: RETRIEVAL DIAGNOSIS FOR ALL REMAINING FALSE NEGATIVES")
print("==================================================================")

fn_cases = []
for p in pred_list:
    cid = p['id']
    gt = gt_map[cid]
    exp_sup = set(gt['expected_supported'])
    pred_sup = set(p['predicted_supported'])
    fn_set = exp_sup - pred_sup
    if fn_set:
        fn_cases.append(cid)

print(f"FN Cases in Phase 2 ({len(fn_cases)} cases): {fn_cases}")

fn_details = []

for cid in fn_cases:
    gt = gt_map[cid]
    pred = pred_map[cid]
    incident = gt['incident']
    exp_sup = gt['expected_supported']
    pred_sup = pred['predicted_supported']
    pred_unc = pred['predicted_uncertain']
    
    missing_fns = [s for s in exp_sup if s not in pred_sup]
    
    # Run exact pipeline retrieval step for diagnosis
    ner_result = extract_entities(incident)
    query_output = generate_queries(ner_result)
    raw_queries = query_output.get("queries", [])
    queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]
    
    all_retrieved_candidates = []
    raw_results_per_query = []
    for q_idx, q_str in enumerate(queries):
        retrieved = retrieve(query=q_str, top_k=20)
        raw_results_per_query.append(retrieved)
        all_retrieved_candidates.extend(retrieved)
        
    reranked = rerank_candidates(incident, all_retrieved_candidates, top_k=15)
    
    for fn_sec in missing_fns:
        # 1. Was in raw top-20?
        found_in_raw = False
        raw_ranks = []
        for q_idx, res_list in enumerate(raw_results_per_query):
            for rank, candidate in enumerate(res_list, start=1):
                sec_num = str(candidate.get('metadata', {}).get('section', ''))
                sec_id = candidate.get('id', '')
                if sec_num == fn_sec or f"bns_{fn_sec}_" in sec_id or f"_{fn_sec}_" in sec_id or sec_id.endswith(f"_{fn_sec}") or sec_id == f"bns_{fn_sec}":
                    found_in_raw = True
                    raw_ranks.append(f"Q{q_idx+1} Rank #{rank} (dist: {round(candidate.get('distance', 0), 4)})")
                    
        # 2. Survived top-15 candidate window?
        in_top_15 = False
        rrf_rank = None
        for rrf_idx, cand in enumerate(reranked, start=1):
            sec_num = str(cand.get('metadata', {}).get('section', ''))
            sec_id = cand.get('id', '')
            if sec_num == fn_sec or f"bns_{fn_sec}_" in sec_id or f"_{fn_sec}_" in sec_id or sec_id.endswith(f"_{fn_sec}") or sec_id == f"bns_{fn_sec}":
                in_top_15 = True
                rrf_rank = rrf_idx
                break
                
        # 3. Decision by analyzer
        analyzer_decision = "NOT_REACHED"
        if in_top_15:
            if fn_sec in pred_unc:
                analyzer_decision = "UNCERTAIN"
            elif fn_sec in pred_sup:
                analyzer_decision = "SUPPORTED"
            else:
                analyzer_decision = "REJECTED/NOT_APPLICABLE"
                
        fn_details.append({
            'case_id': cid,
            'fn_section': fn_sec,
            'retrieved_raw_top20': found_in_raw,
            'raw_ranks': raw_ranks,
            'survived_top15': in_top_15,
            'rrf_rank': rrf_rank,
            'lost_in_rrf': found_in_raw and not in_top_15,
            'reached_analyzer': in_top_15,
            'analyzer_decision': analyzer_decision
        })

for d in fn_details:
    print(f"\nCase {d['case_id']} - Section {d['fn_section']}:")
    print(f"  - Retrieved in raw top-20? {d['retrieved_raw_top20']}")
    print(f"  - Raw rank(s): {d['raw_ranks']}")
    print(f"  - Survived top-15 candidate window? {d['survived_top15']} (RRF Rank: {d['rrf_rank']})")
    print(f"  - Lost during RRF truncation? {d['lost_in_rrf']}")
    print(f"  - Reached legal analyzer? {d['reached_analyzer']}")
    print(f"  - Analyzer decision: {d['analyzer_decision']}")

print("\n==================================================================")
print("SECTION E: QUERY-GENERATION BEHAVIOR")
print("==================================================================")

query_counts = []
fallback_count = 0

for p in pred_list:
    gen_q = p.get('generated_queries', [])
    query_counts.append(len(gen_q))
    if p.get('fallback_used', False):
        fallback_count += 1

print(f"Total benchmark cases: {len(pred_list)}")
print(f"Query counts per case: {query_counts}")
print(f"Average queries per case: {sum(query_counts) / len(query_counts):.2f}")
print(f"Min queries: {min(query_counts)}, Max queries: {max(query_counts)}")
print(f"Fallback cases count: {fallback_count}")

