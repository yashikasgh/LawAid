import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import MockLLMClient, OllamaLLMClient, MultiProviderLLMFailoverClient

gt_path = PROJECT_ROOT / "evaluation" / "ground_truth.json"
preds_path = PROJECT_ROOT / "evaluation" / "predictions.json"

with open(gt_path, "r", encoding="utf-8") as f:
    gt_data = json.load(f)
gt_map = {item["id"]: item for item in gt_data}

with open(preds_path, "r", encoding="utf-8") as f:
    preds_data = json.load(f)
preds_map = {item["id"]: item for item in preds_data}

target_cases = {
    "T04": ["304"],
    "T08": ["303"],
    "T09": ["304"],
    "T12": ["125"],
    "T16": ["318"],
    "T18": ["316"],
    "T29": ["115", "331"]
}

# Try using OllamaLLMClient or Fallback to test query generation
try:
    llm_client = OllamaLLMClient(model_name="qwen2.5:7b")
except Exception:
    llm_client = None

print("=" * 100, flush=True)
print("COMPREHENSIVE DIAGNOSIS OF 7 RETRIEVAL FAILURE CASES", flush=True)
print("=" * 100, flush=True)

for case_id, missed_secs in target_cases.items():
    case_gt = gt_map[case_id]
    case_pred = preds_map[case_id]
    incident_text = case_gt["incident"]
    print(f"\n{'='*70}", flush=True)
    print(f"CASE ID: {case_id} | Category: {case_gt.get('category')}", flush=True)
    print(f"Incident: {incident_text}", flush=True)
    print(f"Expected Supported: {case_gt.get('expected_supported')}", flush=True)
    print(f"Predicted Supported: {case_pred.get('predicted_supported')}", flush=True)
    print(f"Target Missed Section(s): {missed_secs}", flush=True)
    print(f"{'='*70}", flush=True)

    # 1. Check what reached the legal analyzer in predictions.json (top-10 reranked)
    raw_analysis = case_pred.get("raw_analysis", [])
    top10_secs = [str(item.get("section")) for item in raw_analysis]
    top10_doc_ids = [item.get("document_id") for item in case_pred.get("raw_analysis", [])]
    print(f"\n[A] Top-10 Candidates received by Legal Analyzer in Benchmark:", flush=True)
    for idx, item in enumerate(raw_analysis, 1):
        print(f"    #{idx:2d}: Section {item.get('section')} ({item.get('clause')}) - {item.get('title')} | App: {item.get('applicability')}", flush=True)

    # 2. Extract NER
    ner_res = extract_entities(incident_text)

    # 3. Generate Queries using current query generator
    q_out = generate_queries(ner_res, llm_client=llm_client)
    raw_queries = q_out.get("queries", [])
    queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]
    if not queries:
        queries = [incident_text]

    print(f"\n[B] Generated Queries ({len(queries)}):", flush=True)
    for idx, q_obj in enumerate(raw_queries, 1):
        print(f"    Q{idx} [{q_obj.get('query_type')}]: \"{q_obj.get('query')}\"", flush=True)

    # 4. Perform vector search per query and for raw incident
    search_queries = [("RAW_INCIDENT", incident_text)] + [(f"Q{idx+1}_{q_obj.get('query_type')}", q_obj.get('query')) for idx, q_obj in enumerate(raw_queries)]

    all_raw_matches = {} # doc_id -> info
    query_hit_map = {q_label: [] for q_label, _ in search_queries}

    for q_label, q_str in search_queries:
        try:
            ret = retrieve(query=q_str, top_k=20)
            for item in ret:
                doc_id = item.get("id")
                sec = str(item.get("section", ""))
                rank = item.get("rank")
                dist = item.get("distance")

                query_hit_map[q_label].append((sec, doc_id, rank, dist, item.get("title")))

                if doc_id not in all_raw_matches:
                    all_raw_matches[doc_id] = {
                        "sec": sec,
                        "title": item.get("title"),
                        "text": item.get("text"),
                        "hits": []
                    }
                all_raw_matches[doc_id]["hits"].append({
                    "query_label": q_label,
                    "rank": rank,
                    "distance": dist
                })
        except Exception as e:
            print(f"    Error retrieving for {q_label}: {e}", flush=True)

    # 5. Check if target missed sections exist in raw matches
    print(f"\n[C] Raw Candidate Pool Search for Missed Section(s) {missed_secs}:", flush=True)
    for target_sec in missed_secs:
        matching_doc_ids = [doc_id for doc_id, info in all_raw_matches.items() if info["sec"] == target_sec]
        if not matching_doc_ids:
            print(f"    -> Section {target_sec}: ABSENT from raw top-20 pool of ALL queries!", flush=True)
        else:
            print(f"    -> Section {target_sec}: FOUND in raw retrieval candidate pool! Matches:", flush=True)
            for doc_id in matching_doc_ids:
                info = all_raw_matches[doc_id]
                print(f"       Doc ID: {doc_id} | Title: {info['title']}", flush=True)
                for hit in info["hits"]:
                    print(f"         Query [{hit['query_label']}]: Rank #{hit['rank']}, Distance={hit['distance']:.4f}", flush=True)

    # 6. Check Reranking position
    candidate_map = {}
    for q_label, q_str in search_queries:
        if q_label == "RAW_INCIDENT": continue # pipeline uses generated queries
        try:
            ret = retrieve(query=q_str, top_k=20)
            for item in ret:
                doc_id = item.get("id")
                if not doc_id: continue
                if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
                    candidate_map[doc_id] = item
        except Exception:
            pass

    reranked = rerank_candidates(ner_res, list(candidate_map.values()), top_k=None)
    print(f"\n[D] Reranking Positions across total {len(reranked)} unique candidates:", flush=True)
    for target_sec in missed_secs:
        target_positions = [(pos+1, cand) for pos, cand in enumerate(reranked) if str(cand.get("section")) == target_sec]
        if not target_positions:
            print(f"    -> Section {target_sec}: NOT in reranked pool.", flush=True)
        else:
            for pos, cand in target_positions:
                score = cand.get("rerank_score")
                doc_id = cand.get("id")
                status = "RETAINED in Top-10" if pos <= 10 else f"DROPPED BY TOP-10 TRUNCATION (Rank #{pos})"
                print(f"    -> Section {target_sec} ({doc_id}): Rerank Position #{pos} (Score={score:.6f}) -> {status}", flush=True)

print("\n" + "=" * 100, flush=True)
