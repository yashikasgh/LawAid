import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_PATH = PROJECT_ROOT / "evaluation" / "ground_truth.json"
PREDICTIONS_PATH = PROJECT_ROOT / "evaluation" / "predictions.json"
PHASE3_SUMMARY_PATH = PROJECT_ROOT / "scratch" / "phase3_forensic_summary.json"

with open(PREDICTIONS_PATH, "r", encoding="utf-8") as f:
    preds_4a = json.load(f)

with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
    ground_truth = json.load(f)

with open(PHASE3_SUMMARY_PATH, "r", encoding="utf-8") as f:
    phase3_summary = json.load(f)

gt_map = {item["id"]: item for item in ground_truth}
p3_map = {item["case_id"]: item for item in phase3_summary["case_summaries"]}

fp_eliminated = []
fp_still_fp = []
tp_preserved = []
tp_lost = []
fn_recovered = []
fn_still_fn = []

for p in preds_4a:
    case_id = p["id"]
    gt = gt_map.get(case_id, {})
    exp_sup = set(str(s) for s in gt.get("expected_supported", []))
    
    p3_case = p3_map.get(case_id, {})
    p3_sup = set(p3_case.get("predicted_supported", []))
    p3_tp = set(p3_case.get("tp", []))
    p3_fp = set(p3_case.get("fp", []))
    p3_fn = set(p3_case.get("fn", []))

    p4a_sup = set(str(s) for s in p.get("predicted_supported", []))
    p4a_tp = p4a_sup & exp_sup
    p4a_fp = p4a_sup - exp_sup
    p4a_fn = exp_sup - p4a_sup

    # FP transitions
    for sec in p3_fp:
        if sec not in p4a_fp:
            fp_eliminated.append((case_id, sec))
        else:
            fp_still_fp.append((case_id, sec))

    # Any new FP in P4A not in P3?
    for sec in p4a_fp:
        if sec not in p3_fp:
            fp_still_fp.append((case_id, sec))

    # TP transitions
    for sec in p3_tp:
        if sec in p4a_tp:
            tp_preserved.append((case_id, sec))
        else:
            tp_lost.append((case_id, sec))

    # FN transitions
    for sec in p3_fn:
        if sec in p4a_tp:
            fn_recovered.append((case_id, sec))
        else:
            fn_still_fn.append((case_id, sec))

print("==========================================================================================")
print("PHASE 3 -> PHASE 4A TRANSITION BREAKDOWN")
print("==========================================================================================")
print(f"Phase 3 FPs Eliminated in Phase 4A : {len(fp_eliminated)}")
print(f"Phase 3 FPs Remaining in Phase 4A  : {len(fp_still_fp)}")
print(f"Phase 3 TPs Preserved in Phase 4A  : {len(tp_preserved)}")
print(f"Phase 3 TPs Lost in Phase 4A       : {len(tp_lost)}")
print(f"Phase 3 FNs Recovered in Phase 4A  : {len(fn_recovered)}")
print(f"Phase 3 FNs Remaining in Phase 4A  : {len(fn_still_fn)}")

print("\n--- Eliminated FPs Sample ---")
for c, s in fp_eliminated[:15]:
    print(f"Case {c}: Section {s} eliminated")

if tp_lost:
    print("\n--- Lost TPs Detail ---")
    for c, s in tp_lost:
        print(f"Case {c}: Section {s} lost")

if fn_still_fn:
    print("\n--- Remaining FNs Detail ---")
    for c, s in fn_still_fn:
        print(f"Case {c}: Section {s} still FN")
