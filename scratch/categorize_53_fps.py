import json
import os
import sys
import re

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    pred_list = json.load(f)

gt_map = {item['id']: item for item in gt_list}

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
    evidence_doc_ids = pred.get('evidence_document_ids', [])
    raw_analysis = pred.get('raw_analysis', {})
    analysis_items = raw_analysis.get('analysis', []) if isinstance(raw_analysis, dict) else []
    
    for sec_fp in fps:
        # Match item in analysis_items
        matching_item = None
        for item in analysis_items:
            sec_name = str(item.get('section', '')).strip()
            doc_id = str(item.get('document_id', ''))
            if sec_name == sec_fp or f"bns_{sec_fp}" in doc_id:
                matching_item = item
                break
                
        # Primary Root Cause Classification Rules based on section & factual mismatch:
        root_cause = "UNKNOWN"
        explanation = ""
        
        # 1. Section 306 (Theft by clerk/servant) when no master-servant/clerk relation in incident
        if sec_fp == "306":
            root_cause = "A. Missing statutory prerequisite detection"
            explanation = "LLM failed to verify mandatory statutory prerequisite of master-servant / clerk employment relationship before approving Section 306."
            
        # 2. Section 346 (Property mark tampering/misuse) when no property mark in incident
        elif sec_fp == "346":
            root_cause = "A. Missing statutory prerequisite detection"
            explanation = "LLM failed to verify mandatory statutory prerequisite of a property mark or trademark being used or defaced."
            
        # 3. Section 136 (Assault on grave/sudden provocation) when no provocation in incident
        elif sec_fp == "136":
            root_cause = "C. Aggravated/mitigating branch confusion"
            explanation = "LLM approved mitigating assault branch (grave & sudden provocation under Section 136) in general assault/theft incidents without provocation."
            
        # 4. Section 314 (Dishonest misappropriation of lost property) in simple theft/trespass cases
        elif sec_fp == "314":
            root_cause = "D. Related-but-not-applicable provision"
            explanation = "LLM approved Section 314 (misappropriation of unpossessed/lost property) in cases where property was taken directly out of owner's possession (theft)."
            
        # 5. Section 130 (Simple assault/criminal force) alongside §115 (Hurt) or §309 (Robbery)
        elif sec_fp == "130":
            root_cause = "D. Related-but-not-applicable provision"
            explanation = "LLM approved standalone criminal force/assault (§130) as a separate supported offence when physical hurt (§115) or robbery (§309) was the primary charge."
            
        # 6. Section 281 (Rash driving) when no vehicle / driving involved (or in ambiguous cases)
        elif sec_fp == "281":
            if cid in ["T04", "T26"]:
                root_cause = "A. Missing statutory prerequisite detection"
                explanation = "LLM failed to verify vehicle driving / public road endangerment prerequisite (e.g. snatching on foot or simple sidewalk theft)."
            else:
                root_cause = "E. Insufficient incident facts incorrectly treated as sufficient"
                explanation = "LLM treated ambiguous facts as establishing rash driving on public road."

        # 7. Section 106 (Causing death by negligence) when no fatality in incident
        elif sec_fp == "106":
            root_cause = "A. Missing statutory prerequisite detection"
            explanation = "LLM failed to verify mandatory statutory prerequisite of human death/fatality before approving Section 106."

        # 8. Section 125 (Act endangering life causing hurt) when no hurt or vehicle rashness
        elif sec_fp == "125":
            root_cause = "C. Aggravated/mitigating branch confusion"
            explanation = "LLM approved Section 125 alongside Section 281 rash driving without verifying independent Section 125 hurt elements."

        # 9. Section 126 / 127 (Wrongful restraint / confinement) when no obstruction or confinement
        elif sec_fp in ["126", "127"]:
            root_cause = "D. Related-but-not-applicable provision"
            explanation = f"LLM approved Section {sec_fp} (restraint/confinement) as adjacent supported offence without verifying complete physical obstruction."

        # 10. Section 304 (Snatching) in non-snatching cases (or burglary/trespass)
        elif sec_fp == "304":
            root_cause = "C. Aggravated/mitigating branch confusion"
            explanation = "LLM approved Section 304 (Snatching) in house theft or robbery cases where sudden forcible snatching of carried property was absent."

        # 11. Section 305 (Theft in dwelling house) when no dwelling house
        elif sec_fp == "305":
            root_cause = "A. Missing statutory prerequisite detection"
            explanation = "LLM failed to verify building/dwelling house prerequisite before approving Section 305."

        # 12. Section 318 (Cheating) in simple theft / breach of trust cases
        elif sec_fp == "318":
            root_cause = "D. Related-but-not-applicable provision"
            explanation = "LLM approved Section 318 (Cheating by fraudulent inducement) in property theft or house entry cases without fraudulent inducement."

        # 13. Section 351 (Criminal intimidation) when no threat/alarm
        elif sec_fp == "351":
            root_cause = "D. Related-but-not-applicable provision"
            explanation = "LLM approved Section 351 (Criminal intimidation) in robbery/assault cases where no independent threat causing alarm was made."

        # 14. Section 303 (Theft) in non-theft / civil / missing fact cases
        elif sec_fp == "303":
            if cid in ["T26", "T18"]:
                root_cause = "E. Insufficient incident facts incorrectly treated as sufficient"
                explanation = "LLM approved Section 303 theft in ambiguous cases where intent or taking out of possession was unstated/unclear."
            else:
                root_cause = "B. Conditional/proviso prerequisite confusion"
                explanation = "LLM conflated main Section 303 theft with monetary proviso clauses."

        # 15. Cases T26 & T30 (Missing facts / Civil non-criminal)
        elif cid in ["T26", "T30"]:
            root_cause = "E. Insufficient incident facts incorrectly treated as sufficient"
            explanation = "LLM approved statutory provisions in incidents that were civil disputes or contained zero established criminal acts."

        else:
            root_cause = "H. Other"
            explanation = "Adjacent statutory provision approved by LLM analyzer."

        all_fps.append({
            'case_id': cid,
            'category': gt.get('category', ''),
            'incident': incident,
            'fp_section': sec_fp,
            'root_cause': root_cause,
            'explanation': explanation,
            'matching_item': matching_item
        })

print(f"Total Classified FPs: {len(all_fps)}")

# Count distribution
cause_counts = {}
for fp in all_fps:
    rc = fp['root_cause']
    cause_counts[rc] = cause_counts.get(rc, 0) + 1

print("\n=== FP ROOT CAUSE DISTRIBUTION TABLE ===")
print(f"{'Root Cause Category':<55} | {'Count':<8} | {'Percentage':<10}")
print("-" * 80)
for rc in sorted(cause_counts.keys()):
    cnt = cause_counts[rc]
    pct = (cnt / len(all_fps)) * 100
    print(f"{rc:<55} | {cnt:<8} | {pct:.2f}%")

print("\n=== SECTION BREAKDOWN OF 53 FPs ===")
sec_counts = {}
for fp in all_fps:
    s = fp['fp_section']
    sec_counts[s] = sec_counts.get(s, 0) + 1

for s, cnt in sorted(sec_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"Section {s:<5}: {cnt} FP instances ({cnt/len(all_fps)*100:.1f}%)")

