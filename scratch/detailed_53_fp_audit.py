import json
import os
import sys
import re

sys.path.insert(0, os.path.abspath('.'))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    pred_list = json.load(f)

gt_map = {item['id']: item for item in gt_list}
pred_map = {item['id']: item for item in pred_list}

def sanitize(s):
    return str(s).replace("₹", "Rs.").encode("ascii", errors="replace").decode("ascii")

all_fps = []

for pred in pred_list:
    cid = pred['id']
    gt = gt_map[cid]
    incident = gt['incident']
    exp_sup = set(gt['expected_supported'])
    exp_unc = set(gt['expected_uncertain'])
    pred_sup = set(pred['predicted_supported'])
    pred_unc = set(pred['predicted_uncertain'])
    
    fps = sorted(list(pred_sup - exp_sup))
    gen_queries = pred.get('generated_queries', [])
    queries = [q['query'] for q in gen_queries if isinstance(q, dict) and 'query' in q]
    
    raw_analysis = pred.get('raw_analysis', {})
    analysis_items = raw_analysis.get('analysis', []) if isinstance(raw_analysis, dict) else []
    
    evidence_doc_ids = pred.get('evidence_document_ids', [])
    
    # Run exact retrieval step to get raw ranks & RRF ranks for candidates
    raw_results_per_query = []
    all_retrieved = []
    for q_str in queries:
        retrieved = retrieve(query=q_str, top_k=20)
        raw_results_per_query.append(retrieved)
        all_retrieved.extend(retrieved)
        
    reranked = rerank_candidates(incident, all_retrieved, top_k=15)
    
    for sec_fp in fps:
        matching_item = None
        for item in analysis_items:
            sec_name = str(item.get('section', '')).strip()
            doc_id = str(item.get('document_id', ''))
            if sec_name == sec_fp or f"bns_{sec_fp}" in doc_id:
                matching_item = item
                break
                
        # Find raw ranks
        found_in_raw = False
        raw_ranks = []
        target_doc_id = f"bns_{sec_fp}"
        for q_idx, res_list in enumerate(raw_results_per_query, start=1):
            for r_idx, cand in enumerate(res_list, start=1):
                sec_num = str(cand.get('metadata', {}).get('section', ''))
                cand_id = cand.get('id', '')
                if sec_num == sec_fp or f"bns_{sec_fp}_" in cand_id or f"_{sec_fp}_" in cand_id or cand_id.endswith(f"_{sec_fp}") or cand_id == f"bns_{sec_fp}":
                    found_in_raw = True
                    raw_ranks.append(f"Q{q_idx} Rank #{r_idx} (dist: {round(cand.get('distance',0),4)})")
                    target_doc_id = cand_id
                    
        # Find RRF rank
        rrf_rank = None
        for rrf_idx, cand in enumerate(reranked, start=1):
            sec_num = str(cand.get('metadata', {}).get('section', ''))
            cand_id = cand.get('id', '')
            if sec_num == sec_fp or f"bns_{sec_fp}_" in cand_id or f"_{sec_fp}_" in cand_id or cand_id.endswith(f"_{sec_fp}") or cand_id == f"bns_{sec_fp}":
                rrf_rank = rrf_idx
                target_doc_id = cand_id
                break
                
        all_fps.append({
            'case_id': cid,
            'category': gt.get('category', ''),
            'incident': incident,
            'expected_supported': list(exp_sup),
            'expected_uncertain': list(exp_unc),
            'fp_section': sec_fp,
            'target_doc_id': target_doc_id,
            'raw_retrieved': found_in_raw,
            'raw_ranks': raw_ranks,
            'rrf_rank': rrf_rank,
            'in_top_15': rrf_rank is not None,
            'matching_item': matching_item
        })

print(f"Extracted {len(all_fps)} FP items.")

# Print all 53 FPs cleanly
for idx, item in enumerate(all_fps, start=1):
    reasoning = item['matching_item'].get('reasoning', 'No reasoning recorded') if item['matching_item'] else 'No matching item'
    print(f"[{idx}/53] Case {item['case_id']} ({item['category']}) -> FP Section: §{item['fp_section']}")
    print(f"   Incident: {sanitize(item['incident'][:90])}...")
    print(f"   GT Supp: {item['expected_supported']} | Doc ID: {item['target_doc_id']}")
    print(f"   Raw Ranks: {item['raw_ranks']} | RRF Rank: {item['rrf_rank']}")
    print(f"   Reasoning: {sanitize(reasoning)}")
    print()

