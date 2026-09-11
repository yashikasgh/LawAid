import json
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    pred_list = json.load(f)

gt_map = {item['id']: item for item in gt_list}
pred_map = {item['id']: item for item in pred_list}

print("=== FORENSIC 53 FALSE POSITIVES EXTRACTION ===")

fp_records = []

for pred in pred_list:
    cid = pred['id']
    gt = gt_map[cid]
    incident = gt['incident']
    exp_sup = set(gt['expected_supported'])
    exp_unc = set(gt['expected_uncertain'])
    pred_sup = set(pred['predicted_supported'])
    pred_unc = set(pred['predicted_uncertain'])
    
    fps = pred_sup - exp_sup
    
    raw_analysis = pred.get('raw_analysis', {})
    analysis_items = raw_analysis.get('analysis', []) if isinstance(raw_analysis, dict) else []
    
    evidence_doc_ids = pred.get('evidence_document_ids', [])
    
    for sec_fp in sorted(list(fps)):
        # Find item in analysis_items matching sec_fp
        matching_items = []
        for item in analysis_items:
            sec_name = str(item.get('section', '')).strip()
            if sec_name == sec_fp or f"bns_{sec_fp}" in str(item.get('document_id', '')):
                matching_items.append(item)
                
        fp_records.append({
            'case_id': cid,
            'category': gt.get('category', ''),
            'incident': incident,
            'expected_supported': list(exp_sup),
            'expected_uncertain': list(exp_unc),
            'fp_section': sec_fp,
            'evidence_doc_ids': evidence_doc_ids,
            'analysis_matching_items': matching_items
        })

print(f"Total FP Records Extracted: {len(fp_records)}")
for idx, r in enumerate(fp_records, start=1):
    print(f"{idx}. Case {r['case_id']} ({r['category']}): FP Section = {r['fp_section']} | GT Supp = {r['expected_supported']}")

