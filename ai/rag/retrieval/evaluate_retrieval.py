"""evaluate_retrieval.py — Evaluation runner for baseline vector retrieval.

Located at: ai/rag/retrieval/evaluate_retrieval.py
"""

import json
import os
import sys
from pathlib import Path

# Add retrieval package directory to sys.path to support direct import
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from retrieve_bns import retrieve, TOP_K

EVAL_SET_PATH = Path(__file__).resolve().parent.parent / "evaluation" / "retrieval_eval.json"
DISTANCE_WARNING_THRESHOLD = 0.50


def evaluate():
    if not EVAL_SET_PATH.exists():
        print(f"Error: Evaluation set not found at {EVAL_SET_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(EVAL_SET_PATH, "r", encoding="utf-8") as f:
        eval_cases = json.load(f)

    print("=" * 90)
    print("LAWAID RAG - BASELINE RETRIEVAL EVALUATION REPORT")
    print("=" * 90)
    print(f"Evaluation Set     : {EVAL_SET_PATH.resolve()}")
    print(f"Total Test Cases   : {len(eval_cases)}")
    print(f"Top-K              : {TOP_K}")
    print(f"Distance Warning   : > {DISTANCE_WARNING_THRESHOLD}")
    print("=" * 90)

    category_stats = {
        "core_retrieval": {"total": 0, "section_hits": 0, "clause_hits": 0, "clause_applicable": 0},
        "chunking_regression": {"total": 0, "section_hits": 0, "clause_hits": 0, "clause_applicable": 0},
        "known_limitation": {"total": 0, "section_hits": 0, "clause_hits": 0, "clause_applicable": 0}
    }

    for case in eval_cases:
        q_id = case["id"]
        cat = case["category"]
        query = case["query"]
        expected_sec = case.get("expected_section")
        expected_cls = case.get("expected_clause")
        note = case.get("note", "")

        print(f"\n--- [{q_id}] ({cat}) ---")
        print(f"Query: \"{query}\"")
        exp_str = f"Expected Sec: {expected_sec}"
        if expected_cls:
            exp_str += f" | Expected Clause: {expected_cls}"
        if note:
            exp_str += f"\nNote: {note}"
        print(exp_str)

        try:
            top_results = retrieve(query, top_k=TOP_K)
        except Exception as err:
            print(f"Retrieval Error: {err}")
            top_results = []

        print("Retrieved Top-K Results:")
        print(f"  {'Rank':<5} | {'Doc ID':<18} | {'Sec':<5} | {'Clause':<8} | {'Distance':<10} | {'Title'}")
        print("  " + "-" * 75)

        section_hit = False
        clause_hit = False
        sec_hit_rank = None
        cls_hit_rank = None
        hit_distance = None

        for item in top_results:
            rank = item["rank"]
            sec = item["section"]
            cls = item["clause"]
            dist = item["distance"]
            title = item["title"]

            dist_warn = " [WARN: High Distance]" if dist > DISTANCE_WARNING_THRESHOLD else ""
            cls_disp = cls if cls else "-"
            print(f"  {rank:<5} | {item['id']:<18} | {str(sec):<5} | {cls_disp:<8} | {dist:<10.4f}{dist_warn} | {title}")

            # Section Hit check
            if expected_sec is not None and str(sec) == str(expected_sec):
                if not section_hit:
                    section_hit = True
                    sec_hit_rank = rank
                    if not expected_cls:
                        hit_distance = dist

                # Clause Hit check
                if expected_cls and str(cls) == str(expected_cls):
                    if not clause_hit:
                        clause_hit = True
                        cls_hit_rank = rank
                        hit_distance = dist

        # Update stats
        if cat in category_stats:
            category_stats[cat]["total"] += 1
            if section_hit:
                category_stats[cat]["section_hits"] += 1
            if expected_cls:
                category_stats[cat]["clause_applicable"] += 1
                if clause_hit:
                    category_stats[cat]["clause_hits"] += 1

        # Summary line per query
        sec_status = f"PASS (Rank {sec_hit_rank})" if section_hit else "FAIL"
        if expected_cls:
            cls_status = f"PASS (Rank {cls_hit_rank})" if clause_hit else "FAIL"
            overall_status = f"Section Hit: {sec_status} | Clause Hit: {cls_status}"
        else:
            overall_status = f"Section Hit: {sec_status}"

        if hit_distance is not None and hit_distance > DISTANCE_WARNING_THRESHOLD:
            overall_status += f" (Distance Warning: {hit_distance:.4f} > {DISTANCE_WARNING_THRESHOLD})"

        print(f"-> Outcome: {overall_status}")

    # Final Category Summaries
    print("\n" + "=" * 90)
    print("CATEGORY-WISE EVALUATION SUMMARY")
    print("=" * 90)

    for cat_name, stats in category_stats.items():
        tot = stats["total"]
        sec_h = stats["section_hits"]
        cls_h = stats["clause_hits"]
        cls_app = stats["clause_applicable"]

        sec_rate = (sec_h / tot * 100) if tot > 0 else 0.0
        cls_rate = (cls_h / cls_app * 100) if cls_app > 0 else 0.0

        print(f"Category: {cat_name.upper()}")
        print(f"  Total Queries          : {tot}")
        print(f"  Section Hit Rate @ Top-{TOP_K}: {sec_h}/{tot} ({sec_rate:.1f}%)")
        if cls_app > 0:
            print(f"  Clause Hit Rate @ Top-{TOP_K} : {cls_h}/{cls_app} ({cls_rate:.1f}%)")
        if cat_name == "known_limitation":
            print("  Note: known_limitation results are tracked separately and not counted against baseline retrieval accuracy.")
        print("-" * 50)

    print("=" * 90)


if __name__ == "__main__":
    evaluate()
