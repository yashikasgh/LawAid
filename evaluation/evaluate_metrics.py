import json
import csv
import sys
import re
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def normalize_sec(sec_str: str) -> str:
    """Normalize section string for exact matching (e.g. '303(2)' -> '303', 'BNS 134' -> '134')."""
    s = str(sec_str).strip()
    m = re.search(r'\d+', s)
    return m.group(0) if m else s


def run_metrics_evaluation():
    pred_path = PROJECT_ROOT / "evaluation" / "predictions.json"
    if not pred_path.exists():
        print(f"Error: Predictions file not found at {pred_path}. Run run_evaluation.py first.")
        sys.exit(1)

    with open(pred_path, "r", encoding="utf-8") as f:
        predictions = json.load(f)

    total_cases = len(predictions)

    total_tp = 0
    total_fp = 0
    total_fn = 0

    exact_matches = 0
    uncertain_tp = 0
    uncertain_fp = 0
    uncertain_fn = 0

    csv_rows = []
    case_summaries = []

    retrieval_failures = []
    reasoning_failures = []
    missing_fact_failures = []

    # Category performance mapping
    category_results = {}

    for case in predictions:
        cid = case["id"]
        category = case.get("category", "General")
        exp_supp_raw = case.get("expected_supported", [])
        exp_unc_raw = case.get("expected_uncertain", [])
        pred_supp_raw = case.get("predicted_supported", [])
        pred_unc_raw = case.get("predicted_uncertain", [])

        # Normalized sets for matching
        exp_supp = set(normalize_sec(s) for s in exp_supp_raw)
        exp_unc = set(normalize_sec(s) for s in exp_unc_raw)
        pred_supp = set(normalize_sec(s) for s in pred_supp_raw)
        pred_unc = set(normalize_sec(s) for s in pred_unc_raw)

        # TP, FP, FN calculation
        tp_set = pred_supp.intersection(exp_supp)
        fp_set = pred_supp.difference(exp_supp)
        fn_set = exp_supp.difference(pred_supp)

        tp = len(tp_set)
        fp = len(fp_set)
        fn = len(fn_set)

        total_tp += tp
        total_fp += fp
        total_fn += fn

        # Uncertainty TP, FP, FN
        u_tp_set = pred_unc.intersection(exp_unc)
        u_fp_set = pred_unc.difference(exp_unc)
        u_fn_set = exp_unc.difference(pred_unc)

        uncertain_tp += len(u_tp_set)
        uncertain_fp += len(u_fp_set)
        uncertain_fn += len(u_fn_set)

        # Exact match logic (both supported sets match exactly)
        is_exact = (pred_supp == exp_supp)
        if is_exact:
            exact_matches += 1

        # Track Category stats
        if category not in category_results:
            category_results[category] = {"total": 0, "exact": 0, "tp": 0, "fp": 0, "fn": 0}
        category_results[category]["total"] += 1
        if is_exact:
            category_results[category]["exact"] += 1
        category_results[category]["tp"] += tp
        category_results[category]["fp"] += fp
        category_results[category]["fn"] += fn

        # Failure diagnosis
        raw_items = case.get("raw_analysis", [])
        all_retrieved_sections = set()
        for item in raw_items:
            s_norm = normalize_sec(item.get("section", ""))
            if s_norm:
                all_retrieved_sections.add(s_norm)

        for fn_sec in fn_set:
            if fn_sec not in all_retrieved_sections:
                retrieval_failures.append((cid, fn_sec, category))
            else:
                reasoning_failures.append((cid, fn_sec, category))

        if exp_unc and not pred_unc:
            missing_fact_failures.append((cid, list(exp_unc), category))

        csv_rows.append({
            "Case_ID": cid,
            "Category": category,
            "Expected_Supported": ", ".join(exp_supp_raw),
            "Predicted_Supported": ", ".join(pred_supp_raw),
            "Expected_Uncertain": ", ".join(exp_unc_raw),
            "Predicted_Uncertain": ", ".join(pred_unc_raw),
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "Exact_Match": "PASS" if is_exact else "FAIL"
        })

        case_summaries.append({
            "id": cid,
            "category": category,
            "incident": case["incident"],
            "exp_supp": sorted(list(exp_supp)),
            "pred_supp": sorted(list(pred_supp)),
            "tp": sorted(list(tp_set)),
            "fp": sorted(list(fp_set)),
            "fn": sorted(list(fn_set)),
            "is_exact": is_exact
        })

    # Save CSV
    csv_path = PROJECT_ROOT / "evaluation" / "evaluation_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Case_ID", "Category", "Expected_Supported", "Predicted_Supported",
            "Expected_Uncertain", "Predicted_Uncertain", "TP", "FP", "FN", "Exact_Match"
        ])
        writer.writeheader()
        writer.writerows(csv_rows)

    # Compute Global Metrics
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    exact_match_acc = exact_matches / total_cases if total_cases > 0 else 0.0
    fp_rate = total_fp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    fn_rate = total_fn / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0

    u_precision = uncertain_tp / (uncertain_tp + uncertain_fp) if (uncertain_tp + uncertain_fp) > 0 else 0.0
    u_recall = uncertain_tp / (uncertain_tp + uncertain_fn) if (uncertain_tp + uncertain_fn) > 0 else 0.0
    u_f1 = 2 * (u_precision * u_recall) / (u_precision + u_recall) if (u_precision + u_recall) > 0 else 0.0

    # Strongest / Weakest Categories
    cat_perf = []
    for cat, data in category_results.items():
        c_p = data["tp"] / (data["tp"] + data["fp"]) if (data["tp"] + data["fp"]) > 0 else 0.0
        c_r = data["tp"] / (data["tp"] + data["fn"]) if (data["tp"] + data["fn"]) > 0 else 0.0
        c_f1 = 2 * (c_p * c_r) / (c_p + c_r) if (c_p + c_r) > 0 else 0.0
        cat_perf.append((cat, data["total"], data["exact"], c_p, c_r, c_f1))

    cat_perf.sort(key=lambda x: x[5], reverse=True)
    strongest_cats = [c for c in cat_perf if c[5] >= 0.8]
    weakest_cats = [c for c in cat_perf if c[5] < 0.8]

    # Generate evaluation_report.md
    report_path = PROJECT_ROOT / "evaluation" / "evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# LawAid AI Legal Accuracy Evaluation Report\n\n")
        f.write(f"**Total Benchmark Cases**: {total_cases}\n")
        f.write(f"**Evaluation Methodology**: End-to-end BNS 2023 RAG Pipeline evaluation over 30 independent statutory cases.\n\n")

        f.write("## 1. Executive Summary Metrics\n\n")
        f.write("| Metric | Value |\n")
        f.write("| :--- | :---: |\n")
        f.write(f"| **True Positives (TP)** | {total_tp} |\n")
        f.write(f"| **False Positives (FP)** | {total_fp} |\n")
        f.write(f"| **False Negatives (FN)** | {total_fn} |\n")
        f.write(f"| **Precision (Micro)** | {precision:.4f} ({precision*100:.2f}%) |\n")
        f.write(f"| **Recall (Micro)** | {recall:.4f} ({recall*100:.2f}%) |\n")
        f.write(f"| **F1 Score (Micro)** | {f1:.4f} ({f1*100:.2f}%) |\n")
        f.write(f"| **Exact-Match Accuracy** | {exact_match_acc:.4f} ({exact_match_acc*100:.2f}%) [{exact_matches}/{total_cases}] |\n")
        f.write(f"| **False-Positive Rate** | {fp_rate:.4f} ({fp_rate*100:.2f}%) |\n")
        f.write(f"| **False-Negative Rate** | {fn_rate:.4f} ({fn_rate*100:.2f}%) |\n")
        f.write(f"| **Uncertainty F1 Score** | {u_f1:.4f} ({u_f1*100:.2f}%) |\n\n")

        f.write("## 2. Category Performance Breakdown\n\n")
        f.write("| Category | Total Cases | Exact Matches | Precision | Recall | F1 Score |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
        for cat, total, exact, c_p, c_r, c_f1 in cat_perf:
            f.write(f"| {cat} | {total} | {exact} | {c_p*100:.1f}% | {c_r*100:.1f}% | **{c_f1*100:.1f}%** |\n")
        f.write("\n")

        f.write("## 3. Error & Failure Diagnostic Analysis\n\n")
        f.write(f"- **Retrieval Failures**: {len(retrieval_failures)} instances (expected section not present in candidate pool).\n")
        for cid, sec, cat in retrieval_failures:
            f.write(f"  - Case {cid} ({cat}): Section {sec} failed retrieval.\n")

        f.write(f"- **Legal Reasoning Failures**: {len(reasoning_failures)} instances (section retrieved but rejected or missed by LLM).\n")
        for cid, sec, cat in reasoning_failures:
            f.write(f"  - Case {cid} ({cat}): Section {sec} retrieved but LLM failed to mark supported.\n")

        f.write(f"- **Missing-Fact Handling Failures**: {len(missing_fact_failures)} instances.\n")
        for cid, secs, cat in missing_fact_failures:
            f.write(f"  - Case {cid} ({cat}): Expected uncertainty for {secs} missed.\n")

        f.write("\n## 4. Final Verdict\n\n")
        verdict_pass = (f1 >= 0.80) and (exact_match_acc >= 0.70)
        if verdict_pass:
            f.write(f"**VERDICT: SUPPORTED** — LawAid achieves an overall F1 score of **{f1*100:.2f}%** and Exact-Match Accuracy of **{exact_match_acc*100:.2f}%**, exceeding the ≥80% legal-analysis accuracy benchmark threshold.\n")
        else:
            f.write(f"**VERDICT: NOT YET FULLY SUPPORTED** — LawAid achieves an F1 score of **{f1*100:.2f}%** and Exact-Match Accuracy of **{exact_match_acc*100:.2f}%**. Specific category recall or retrieval gaps require further targeted improvements.\n")

    # Print summary to console
    print("\n" + "=" * 90)
    print("BENCHMARK METRICS SUMMARY REPORT")
    print("=" * 90)
    print(f"Total Benchmark Cases : {total_cases}")
    print(f"True Positives (TP)   : {total_tp}")
    print(f"False Positives (FP)  : {total_fp}")
    print(f"False Negatives (FN)  : {total_fn}")
    print(f"Precision             : {precision:.4f} ({precision*100:.2f}%)")
    print(f"Recall                : {recall:.4f} ({recall*100:.2f}%)")
    print(f"F1 Score              : {f1:.4f} ({f1*100:.2f}%)")
    print(f"Exact-Match Accuracy  : {exact_match_acc:.4f} ({exact_match_acc*100:.2f}%) [{exact_matches}/{total_cases}]")
    print(f"False Positive Rate   : {fp_rate:.4f} ({fp_rate*100:.2f}%)")
    print(f"False Negative Rate   : {fn_rate:.4f} ({fn_rate*100:.2f}%)")
    print(f"Uncertainty F1 Score  : {u_f1:.4f} ({u_f1*100:.2f}%)")
    print("=" * 90)


if __name__ == "__main__":
    run_metrics_evaluation()
