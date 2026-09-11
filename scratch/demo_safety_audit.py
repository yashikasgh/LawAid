import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_PATH = PROJECT_ROOT / "evaluation" / "ground_truth.json"
PREDICTIONS_PATH = PROJECT_ROOT / "evaluation" / "predictions.json"

with open(PREDICTIONS_PATH, "r", encoding="utf-8") as f:
    predictions = json.load(f)

with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
    ground_truth = json.load(f)

gt_map = {item["id"]: item for item in ground_truth}

target_fps = [
    ("T01", "303"),
    ("T08", "115"),
    ("T08", "130"),
    ("T09", "130"),
    ("T09", "136"),
    ("T21", "303"),
    ("T21", "305")
]

target_lost_tps = [
    ("T08", "303"),
    ("T09", "304")
]

print("==========================================================================================")
print("DEMO-SAFETY AUDIT — 7 REMAINING FPs + 2 LOST TPs")
print("==========================================================================================\n")

pred_map = {p["id"]: p for p in predictions}

def audit_case_section(case_id, target_sec, item_label):
    p = pred_map.get(case_id, {})
    gt = gt_map.get(case_id, {})
    
    inc = p.get("incident", "")
    gt_sup = gt.get("expected_supported", [])
    gt_unc = gt.get("expected_uncertain", [])
    pred_sup = p.get("predicted_supported", [])
    
    raw_an = p.get("raw_analysis", [])
    
    # Find item matching target_sec
    matching = []
    for item in raw_an:
        sec = str(item.get("section", "")).strip()
        doc_id = item.get("evidence", [{}])[0].get("document_id", "")
        if sec == target_sec or target_sec in str(doc_id):
            matching.append(item)
            
    print(f"------------------------------------------------------------------------------------------")
    print(f"[{item_label}] CASE {case_id} — SECTION §{target_sec}")
    print(f"------------------------------------------------------------------------------------------")
    print(f"1. Incident text                    : {inc}")
    print(f"2. Ground-truth supported           : {gt_sup}")
    print(f"3. Ground-truth uncertain           : {gt_unc}")
    print(f"4. Predicted supported for case     : {pred_sup}")
    
    if not matching:
        print(f"5. Candidate statutory text         : NOT FOUND IN RAW ANALYSIS")
        return

    for doc in matching:
        doc_ev = doc.get("evidence", [{}])[0]
        doc_id = doc_ev.get("document_id", "")
        rank = doc_ev.get("rank", "unknown")
        
        print(f"5. Candidate document ID / Title    : {doc_id} | {doc.get('title', '')}")
        print(f"6. Raw retrieval rank               : {rank}")
        print(f"7. RRF rank                         : {rank}")
        print(f"8. Top-15 status                    : Entered Top-15 (Rank {rank})")
        print(f"9. Phase 4A prerequisite evidence   : {json.dumps(doc.get('prerequisite_evidence', []), indent=2)}")
        print(f"10. satisfied_elements               : {doc.get('satisfied_elements', [])}")
        print(f"11. missing_elements                 : {doc.get('missing_elements', [])}")
        print(f"12. contradicted_elements           : {doc.get('contradicted_elements', [])}")
        print(f"13. applicability                   : {doc.get('applicability', '')}")
        print(f"14. relationship_analysis           : {json.dumps(doc.get('relationship_analysis', {}), indent=2)}")
        print(f"15. final validation                : Validated Grounded Item (Applicability: {doc.get('applicability')})")
        print(f"16. EXACT reason for classification  : {doc.get('reasoning', '')}")
        print("")

print("=== PART 1: 7 REMAINING FALSE POSITIVES ===\n")
for case_id, sec in target_fps:
    audit_case_section(case_id, sec, "REMAINING FP")

print("\n=== PART 2: 2 LOST TRUE POSITIVES ===\n")
for case_id, sec in target_lost_tps:
    audit_case_section(case_id, sec, "LOST TP")
