import json
import sys

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)
    gt_map = {item['id']: item for item in gt_list}

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    preds = json.load(f)

out_lines = []

for p in preds:
    cid = p['id']
    gt = gt_map[cid]
    exp_supp = set(gt['expected_supported'])
    exp_unc = set(gt['expected_uncertain'])
    pred_supp = set(p['predicted_supported'])
    pred_unc = set(p['predicted_uncertain'])
    
    raw = p.get('raw_analysis', [])
    cand_sections = []
    cand_doc_ids = []
    for item in raw:
        sec = str(item.get('section'))
        if sec and sec not in cand_sections:
            cand_sections.append(sec)
        for ev in item.get('evidence', []):
            doc_id = ev.get('document_id')
            if doc_id and doc_id not in cand_doc_ids:
                cand_doc_ids.append(doc_id)
                
    cat = gt['category']
    out_lines.append(f"=== CASE {cid}: {cat} ===")
    out_lines.append(f"Incident: {gt['incident']}")
    out_lines.append(f"GT Supported: {sorted(list(exp_supp))}")
    out_lines.append(f"GT Uncertain: {sorted(list(exp_unc))}")
    out_lines.append(f"Pred Supported: {sorted(list(pred_supp))}")
    out_lines.append(f"Pred Uncertain: {sorted(list(pred_unc))}")
    out_lines.append(f"Candidate Sections (Top 10): {cand_sections}")
    out_lines.append(f"Candidate Doc IDs: {cand_doc_ids}")
    
    tp_supp = exp_supp.intersection(pred_supp)
    fp_supp = pred_supp.difference(exp_supp)
    fn_supp = exp_supp.difference(pred_supp)
    out_lines.append(f"TP (Supported): {sorted(list(tp_supp))}")
    out_lines.append(f"FP (Supported): {sorted(list(fp_supp))}")
    out_lines.append(f"FN (Supported): {sorted(list(fn_supp))}")

    for s in sorted(list(exp_supp)):
        in_cand = s in cand_sections
        out_lines.append(f"  Expected section {s} in candidates? {in_cand}")
        if in_cand:
            decisions = []
            for item in raw:
                if str(item.get('section')) == s:
                    decisions.append((item.get('clause'), item.get('applicability'), item.get('reasoning')))
            out_lines.append(f"  LLM decisions for section {s}: {decisions}")

    out_lines.append("\n" + "="*80 + "\n")

with open('evaluation/case_analysis_log.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))

print("Wrote evaluation/case_analysis_log.txt successfully.")
