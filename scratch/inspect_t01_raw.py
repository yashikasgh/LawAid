import json

with open("evaluation/predictions.json", "r", encoding="utf-8") as f:
    preds = json.load(f)

for p in preds:
    if p["id"] == "T01":
        print("T01 predicted_supported:", p.get("predicted_supported"))
        print("T01 predicted_uncertain:", p.get("predicted_uncertain"))
        print("T01 predicted_not_supported:", p.get("predicted_not_supported"))
        for item in p.get("raw_analysis", []):
            print(f"Sec: {item.get('section')} | Clause: {item.get('clause')} | App: {item.get('applicability')} | DocID: {item.get('evidence', [{}])[0].get('document_id')}")
