import json

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    pred_list = json.load(f)

gt_map = {item['id']: item for item in gt_list}
pred_map = {item['id']: item for item in pred_list}

print("=== SECTION E: QUERY GENERATION BEHAVIOR ===")
query_counts = []
fallback_count = 0
for p in pred_list:
    gen_q = p.get('generated_queries', [])
    query_counts.append(len(gen_q))
    if p.get('fallback_used', False):
        fallback_count += 1

print(f"Total benchmark cases: {len(pred_list)}")
print(f"Query counts per case: {query_counts}")
print(f"Average query count: {sum(query_counts)/len(query_counts):.2f}")
print(f"Min queries: {min(query_counts)}, Max queries: {max(query_counts)}")
print(f"Fallback cases count: {fallback_count}")

# Sample multi-perspective queries from pred_list
print("\nSample queries from T01:")
print(pred_map['T01'].get('generated_queries', []))
print("\nSample queries from T08:")
print(pred_map['T08'].get('generated_queries', []))
print("\nSample queries from T29:")
print(pred_map['T29'].get('generated_queries', []))


print("\n=== SECTION C: FN DIAGNOSIS FROM PREDICTIONS ===")
fn_cases = ['T04', 'T08', 'T09', 'T16', 'T18', 'T29']

for cid in fn_cases:
    gt = gt_map[cid]
    p = pred_map[cid]
    exp_sup = set(gt['expected_supported'])
    pred_sup = set(p['predicted_supported'])
    pred_unc = set(p['predicted_uncertain'])
    evidence_ids = p.get('evidence_document_ids', [])
    raw_analysis = p.get('raw_analysis', {})
    
    missing_fns = exp_sup - pred_sup
    print(f"\n--- CASE {cid} ---")
    print(f"Incident: {gt['incident']}")
    print(f"Expected Supported: {list(exp_sup)}")
    print(f"Predicted Supported: {list(pred_sup)}")
    print(f"Predicted Uncertain: {list(pred_unc)}")
    print(f"Missing FN Section(s): {list(missing_fns)}")
    print(f"Evidence Document IDs in Candidate Pool ({len(evidence_ids)}): {evidence_ids}")
    
    for fn_sec in missing_fns:
        # Check if fn_sec is in evidence_ids
        in_candidates = any(fn_sec in doc_id or f"_{fn_sec}_" in doc_id or doc_id.endswith(f"_{fn_sec}") for doc_id in evidence_ids)
        print(f"  Section {fn_sec}:")
        print(f"    - Reached top-15 candidate pool? {in_candidates}")
        if in_candidates:
            if fn_sec in pred_unc:
                print(f"    - Analyzer decision: UNCERTAIN (marked uncertain instead of supported)")
            else:
                print(f"    - Analyzer decision: REJECTED / NOT_APPLICABLE by LLM legal analyzer")
        else:
            print(f"    - Analyzer decision: NOT_REACHED (Retrieval failure / lost before top-15 pool)")

