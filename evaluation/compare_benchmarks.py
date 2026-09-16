import json
import re
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Parse baseline from case_analysis_log.txt
baseline_cases = {}
with open('evaluation/case_analysis_log.txt', 'r', encoding='utf-8') as f:
    text = f.read()

case_blocks = text.split("================================================================================")
for block in case_blocks:
    m_id = re.search(r"=== CASE (T\d+): (.*?) ===", block)
    if not m_id:
        continue
    cid = m_id.group(1)
    cat = m_id.group(2)
    
    m_gt_supp = re.search(r"GT Supported: (\[.*?\])", block)
    m_gt_unc = re.search(r"GT Uncertain: (\[.*?\])", block)
    m_pred_supp = re.search(r"Pred Supported: (\[.*?\])", block)
    m_pred_unc = re.search(r"Pred Uncertain: (\[.*?\])", block)
    
    gt_supp = eval(m_gt_supp.group(1)) if m_gt_supp else []
    gt_unc = eval(m_gt_unc.group(1)) if m_gt_unc else []
    pred_supp = eval(m_pred_supp.group(1)) if m_pred_supp else []
    pred_unc = eval(m_pred_unc.group(1)) if m_pred_unc else []
    
    baseline_cases[cid] = {
        'id': cid,
        'category': cat,
        'gt_supported': gt_supp,
        'gt_uncertain': gt_unc,
        'pred_supported': pred_supp,
        'pred_uncertain': pred_unc
    }

# Parse Post-Phase 1 from predictions.json
with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    preds_post = json.load(f)

post_cases = {p['id']: p for p in preds_post}

print(f"Loaded {len(baseline_cases)} baseline cases and {len(post_cases)} post-Phase-1 cases.\n")

changed_cases = []

total_base_tp = 0
total_base_fp = 0
total_base_fn = 0

total_post_tp = 0
total_post_fp = 0
total_post_fn = 0

for cid in sorted(baseline_cases.keys()):
    base = baseline_cases[cid]
    post = post_cases[cid]
    
    gt_supp = set(base['gt_supported'])
    gt_unc = set(base['gt_uncertain'])
    
    base_supp = set(base['pred_supported'])
    base_unc = set(base['pred_uncertain'])
    
    post_supp = set(post.get('predicted_supported') or [])
    post_unc = set(post.get('predicted_uncertain') or [])
    
    # Baseline TP/FP/FN
    b_tp = gt_supp.intersection(base_supp)
    b_fp = base_supp.difference(gt_supp)
    b_fn = gt_supp.difference(base_supp)
    
    total_base_tp += len(b_tp)
    total_base_fp += len(b_fp)
    total_base_fn += len(b_fn)
    
    # Post TP/FP/FN
    p_tp = gt_supp.intersection(post_supp)
    p_fp = post_supp.difference(gt_supp)
    p_fn = gt_supp.difference(post_supp)
    
    total_post_tp += len(p_tp)
    total_post_fp += len(p_fp)
    total_post_fn += len(p_fn)
    
    supp_changed = (base_supp != post_supp)
    unc_changed = (base_unc != post_unc)
    
    if supp_changed or unc_changed:
        removed_supp = base_supp.difference(post_supp)
        added_supp = post_supp.difference(base_supp)
        
        removed_unc = base_unc.difference(post_unc)
        added_unc = post_unc.difference(base_unc)
        
        changed_cases.append({
            'id': cid,
            'category': base['category'],
            'gt_supported': sorted(list(gt_supp)),
            'gt_uncertain': sorted(list(gt_unc)),
            'base_supported': sorted(list(base_supp)),
            'base_uncertain': sorted(list(base_unc)),
            'post_supported': sorted(list(post_supp)),
            'post_uncertain': sorted(list(post_unc)),
            'removed_supported': sorted(list(removed_supp)),
            'added_supported': sorted(list(added_supp)),
            'removed_uncertain': sorted(list(removed_unc)),
            'added_uncertain': sorted(list(added_unc)),
            'raw_analysis_post': post.get('raw_analysis', [])
        })

print(f"BASELINE METRICS: TP={total_base_tp}, FP={total_base_fp}, FN={total_base_fn}")
print(f"POST METRICS    : TP={total_post_tp}, FP={total_post_fp}, FN={total_post_fn}")
print(f"TOTAL CHANGED CASES: {len(changed_cases)}\n")

for c in changed_cases:
    print(f"=== CASE {c['id']}: {c['category']} ===")
    print(f"  GT Supp : {c['gt_supported']}, GT Unc: {c['gt_uncertain']}")
    print(f"  Base Supp: {c['base_supported']}, Base Unc: {c['base_uncertain']}")
    print(f"  Post Supp: {c['post_supported']}, Post Unc: {c['post_uncertain']}")
    print(f"  Removed Supp: {c['removed_supported']}, Added Supp: {c['added_supported']}")
    print(f"  Removed Unc : {c['removed_uncertain']}, Added Unc : {c['added_uncertain']}")
    
    # Classify changes
    for s in c['removed_supported']:
        if s in c['gt_supported']:
            print(f"    -> [TRUE POSITIVE REMOVED / FALSE NEGATIVE CREATED]: Section {s} was in GT supported but removed in Post-Phase-1.")
        else:
            print(f"    -> [FALSE POSITIVE REMOVED]: Section {s} was NOT in GT supported and correctly removed in Post-Phase-1.")
            
    for s in c['added_supported']:
        if s in c['gt_supported']:
            print(f"    -> [TRUE POSITIVE CREATED]: Section {s} was in GT supported and newly added in Post-Phase-1.")
        else:
            print(f"    -> [FALSE POSITIVE CREATED]: Section {s} was NOT in GT supported and newly added in Post-Phase-1.")
            
    print("\n" + "-"*60 + "\n")
