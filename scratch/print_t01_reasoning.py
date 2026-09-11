import json

with open("evaluation/predictions.json", "r", encoding="utf-8") as f:
    preds = json.load(f)

for p in preds:
    if p["id"] == "T01":
        for item in p.get("raw_analysis", []):
            if item.get("applicability") == "supported":
                print(f"Sec: {item.get('section')} | DocID: {item.get('evidence', [{}])[0].get('document_id')} | Reason: {item.get('reasoning')}")
