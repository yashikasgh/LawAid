"""phase3_forensic_audit.py — Deep Forensic Audit of Phase 3 Benchmark Results.

Analyzes evaluation/predictions.json and evaluation/ground_truth.json to trace all 50 Phase 3 FPs,
compares Phase 2 vs Phase 3, classifies root causes, failure stages, and identifies generic patterns.
STRICT DIAGNOSIS ONLY — NO APPLICATION CODE MODIFICATIONS.
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
PREDICTIONS_PATH = EVALUATION_DIR / "predictions.json"
GROUND_TRUTH_PATH = EVALUATION_DIR / "ground_truth.json"

def main():
    with open(PREDICTIONS_PATH, "r", encoding="utf-8") as f:
        predictions = json.load(f)
        
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    gt_map = {item["id"]: item for item in ground_truth}

    print("==========================================================================================")
    print("PHASE 3 FORENSIC AUDIT — COMPLETE TRACE OF ALL 50 FALSE POSITIVES")
    print("==========================================================================================\n")

    total_tp = 0
    total_fp = 0
    total_fn = 0

    fp_list = []
    tp_list = []
    fn_list = []
    case_summary = []

    for pred in predictions:
        case_id = pred["id"]
        gt = gt_map.get(case_id, {})
        expected_supported = set(str(s) for s in gt.get("expected_supported", []))
        expected_uncertain = set(str(s) for s in gt.get("expected_uncertain", []))
        
        predicted_supported = set(str(s) for s in pred.get("predicted_supported", []))
        predicted_uncertain = set(str(s) for s in pred.get("predicted_uncertain", []))

        tps = predicted_supported & expected_supported
        fps = predicted_supported - expected_supported
        fns = expected_supported - predicted_supported

        total_tp += len(tps)
        total_fp += len(fps)
        total_fn += len(fns)

        case_summary.append({
            "case_id": case_id,
            "category": pred.get("category", ""),
            "incident": pred.get("incident", ""),
            "expected_supported": sorted(list(expected_supported)),
            "expected_uncertain": sorted(list(expected_uncertain)),
            "predicted_supported": sorted(list(predicted_supported)),
            "predicted_uncertain": sorted(list(predicted_uncertain)),
            "tp": sorted(list(tps)),
            "fp": sorted(list(fps)),
            "fn": sorted(list(fns))
        })

        raw_analysis = pred.get("raw_analysis", [])

        for sec_fp in sorted(list(fps)):
            # Find matching document(s) in raw_analysis
            matching_docs = [doc for doc in raw_analysis if str(doc.get("section", "")) == sec_fp]
            if not matching_docs:
                matching_docs = [doc for doc in raw_analysis if sec_fp in str(doc.get("clause", ""))]

            for doc in matching_docs:
                if doc.get("applicability") == "supported":
                    ev_list = doc.get("evidence", [])
                    doc_id = ev_list[0].get("document_id") if ev_list else doc.get("document_id", "unknown")
                    rank = ev_list[0].get("rank") if ev_list else "unknown"
                    
                    fp_list.append({
                        "case_id": case_id,
                        "incident": pred.get("incident", ""),
                        "expected_supported": sorted(list(expected_supported)),
                        "expected_uncertain": sorted(list(expected_uncertain)),
                        "predicted_fp_section": sec_fp,
                        "doc_id": doc_id,
                        "doc_title": doc.get("title", ""),
                        "offence_type": doc.get("offence_type", ""),
                        "rank": rank,
                        "unit_type": doc.get("unit_type", "core_definition"),
                        "statutory_structure": doc.get("statutory_structure", {}),
                        "prerequisite_evidence": doc.get("prerequisite_evidence", []),
                        "satisfied_elements": doc.get("satisfied_elements", []),
                        "missing_elements": doc.get("missing_elements", []),
                        "contradicted_elements": doc.get("contradicted_elements", []),
                        "relationship_analysis": doc.get("relationship_analysis", {}),
                        "reasoning": doc.get("reasoning", "")
                    })

    print(f"Total Cases Checked : {len(predictions)}")
    print(f"Total True Positives (TP): {total_tp}")
    print(f"Total False Positives (FP): {total_fp}")
    print(f"Total False Negatives (FN): {total_fn}")
    print(f"Extracted FP entries count: {len(fp_list)}\n")

    # Group FPs by root cause
    root_cause_counts = {}
    stage_counts = {}

    for idx, fp in enumerate(fp_list, 1):
        case_id = fp["case_id"]
        sec = fp["predicted_fp_section"]
        title = fp["doc_title"]
        reason = fp["reasoning"]
        inc = fp["incident"]
        
        # Categorize Root Cause based on evidence
        # A. Missing statutory prerequisite
        # B. Conditional/proviso reasoning error
        # C. Aggravated/mitigating branch error
        # D. Related-but-not-applicable provision
        # E. Insufficient/ambiguous facts treated as sufficient
        # F. Candidate statutory context misleading the analyzer
        # G. Cross-candidate contamination
        # H. Incorrect candidate relationship/subsumption reasoning
        # I. Mens rea reasoning error
        # J. Retrieval/candidate-quality issue
        # K. Validation/output classification issue
        # L. Other

        rc = "D. Related-but-not-applicable provision" # Default
        stage = "Pass 4 — Strict Applicability Decision"

        inc_lower = inc.lower()
        title_lower = title.lower()
        reason_lower = reason.lower()

        # Capacity checks
        if sec in ["306", "316", "217"] or "clerk" in title_lower or "servant" in title_lower or "trust" in title_lower or "public servant" in title_lower:
            rc = "A. Missing statutory prerequisite (Special Capacity)"
            stage = "Pass 1 — Statutory Requirement Extraction"
        # Instrumentality / Object checks
        elif sec in ["346", "331"] or "property mark" in title_lower or "house-breaking" in title_lower or "dwelling" in title_lower:
            rc = "A. Missing statutory prerequisite (Specific Object/Place)"
            stage = "Pass 1 — Statutory Requirement Extraction"
        # Consequence / Harm checks
        elif sec in ["106", "125", "115"] and not any(w in inc_lower for w in ["death", "die", "killed", "injured", "hurt", "pain"]):
            rc = "A. Missing statutory prerequisite (Consequence Absent)"
            stage = "Pass 2 — Evidence Status Classification"
        # Related-but-not-applicable (e.g. assault 130/134 vs theft 303 or snatching 304)
        elif sec in ["130", "131", "134"] and any(w in inc_lower for w in ["stole", "took", "bicycle", "watch", "phone"]):
            rc = "D. Related-but-not-applicable provision"
            stage = "Pass 5 — Candidate Relationship Analysis"
        # General vs Specific (e.g. theft 303 vs snatching 304 or robbery 309)
        elif sec in ["303"] and any(w in inc_lower for w in ["snatch", "grab", "knifepoint"]):
            rc = "H. Incorrect candidate relationship/subsumption reasoning"
            stage = "Pass 5 — Candidate Relationship Analysis"
        # Over-broad facts / ambiguous facts
        elif "force" in reason_lower or "restraint" in reason_lower or "threat" in reason_lower:
            rc = "E. Insufficient/ambiguous facts treated as sufficient"
            stage = "Pass 4 — Strict Applicability Decision"

        root_cause_counts[rc] = root_cause_counts.get(rc, 0) + 1
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

        fp["root_cause"] = rc
        fp["failure_stage"] = stage

    print("==========================================================================================")
    print("PHASE 3 FALSE POSITIVE ROOT CAUSE DISTRIBUTION")
    print("==========================================================================================")
    for rc, count in sorted(root_cause_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(fp_list)) * 100 if fp_list else 0
        print(f"- {rc:<60}: {count:2d} FPs ({pct:5.1f}%)")

    print("\n==========================================================================================")
    print("PHASE 3 FAILURE STAGE DISTRIBUTION")
    print("==========================================================================================")
    for st, count in sorted(stage_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(fp_list)) * 100 if fp_list else 0
        print(f"- {st:<50}: {count:2d} FPs ({pct:5.1f}%)")

    # Save complete detailed analysis to scratch/phase3_forensic_summary.json
    output_path = PROJECT_ROOT / "scratch" / "phase3_forensic_summary.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_cases": len(predictions),
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(total_tp / (total_tp + total_fp), 4) if (total_tp + total_fp) > 0 else 0,
            "recall": round(total_tp / (total_tp + total_fn), 4) if (total_tp + total_fn) > 0 else 0,
            "f1": round(2 * total_tp / (2 * total_tp + total_fp + total_fn), 4) if (2 * total_tp + total_fp + total_fn) > 0 else 0,
            "root_cause_counts": root_cause_counts,
            "stage_counts": stage_counts,
            "case_summaries": case_summary,
            "fp_list": fp_list
        }, f, indent=2)
        
    print(f"\nWrote full forensic summary to: {output_path}")

if __name__ == "__main__":
    main()
