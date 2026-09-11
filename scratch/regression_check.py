import json

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    pred_list = json.load(f)

gt_map = {item['id']: item for item in gt_list}
pred_map = {item['id']: item for item in pred_list}

# Phase 1 Core vs Conditional Refinement predictions summary from earlier log/reports
# Let's inspect each case in Phase 2 predictions.json:
# Check which cases were fully correct in Phase 1 Core vs Conditional Refinement:
# In Phase 1 Refinement:
# TP=23, FP=34, FN=12, Precision=40.35%, Recall=65.71%, F1=50.00%, Exact-Match=30.00% (9 cases correct)
# In Phase 2:
# TP=26, FP=53, FN=9, Precision=32.91%, Recall=74.29%, F1=45.61%, Exact-Match=26.67% (8 cases correct)

print("=== EXACT MATCHES IN PHASE 2 ===")
p2_correct_cases = []
for p in pred_list:
    cid = p['id']
    gt = gt_map[cid]
    exp_sup = set(gt['expected_supported'])
    pred_sup = set(p['predicted_supported'])
    if pred_sup == exp_sup:
        p2_correct_cases.append(cid)

print(f"Phase 2 Exact Match Cases ({len(p2_correct_cases)}): {p2_correct_cases}")

# Exact match cases in Phase 1 Refinement (9 cases):
# T10, T13, T15, T17, T22, T23, T24, T27, T30
# Let's check which of these 9 cases are NO LONGER exact matches in Phase 2:
p1_correct_cases = ['T10', 'T13', 'T15', 'T17', 'T22', 'T23', 'T24', 'T27', 'T30']

regressed_cases = [c for c in p1_correct_cases if c not in p2_correct_cases]
print(f"\nRegressed Cases (Correct in Phase 1 Refinement, Incorrect in Phase 2): {regressed_cases}")

for cid in regressed_cases:
    gt = gt_map[cid]
    p = pred_map[cid]
    print(f"\n--- Regressed Case {cid} ---")
    print(f"Ground Truth Expected Supported: {gt['expected_supported']}")
    print(f"Phase 2 Predicted Supported: {p['predicted_supported']}")
    print(f"Phase 2 Predicted Uncertain: {p['predicted_uncertain']}")
    print(f"Phase 2 Candidate Doc IDs: {p.get('evidence_document_ids', [])}")

