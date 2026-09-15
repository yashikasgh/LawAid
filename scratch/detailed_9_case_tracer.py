import json

with open("evaluation/predictions.json", "r", encoding="utf-8") as f:
    predictions = json.load(f)

with open("evaluation/ground_truth.json", "r", encoding="utf-8") as f:
    ground_truth = json.load(f)

gt_map = {item["id"]: item for item in ground_truth}

print("==========================================================================================")
print("EXACT CASE-BY-CASE FP AND LOST TP RECONCILIATION")
print("==========================================================================================\n")

for p in predictions:
    cid = p["id"]
    gt = gt_map.get(cid, {})
    gt_sup = set(str(s) for s in gt.get("expected_supported", []))
    pred_sup = set(str(s) for s in p.get("predicted_supported", []))
    
    fps = pred_sup - gt_sup
    fns = gt_sup - pred_sup
    tps = pred_sup & gt_sup
    
    if fps or fns:
        print(f"Case {cid} [{p.get('category')}]")
        print(f"  Incident: {p.get('incident')}")
        print(f"  GT Supported: {sorted(list(gt_sup))}")
        print(f"  Pred Supported: {sorted(list(pred_sup))}")
        print(f"  TPs: {sorted(list(tps))}")
        print(f"  FPs: {sorted(list(fps))}")
        print(f"  FNs: {sorted(list(fns))}")
        print("  Raw Analysis Items:")
        for item in p.get("raw_analysis", []):
            sec = item.get("section")
            app = item.get("applicability")
            reason = item.get("reasoning")
            doc_id = item.get("evidence", [{}])[0].get("document_id")
            if app in ["supported", "uncertain"] or str(sec) in gt_sup:
                print(f"    - Sec {sec} ({doc_id}) -> {app.upper()} | Reason: {reason}")
        print("")
