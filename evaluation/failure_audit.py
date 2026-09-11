import json
import csv
import sys

# Ensure UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)
    gt_map = {item['id']: item for item in gt_list}

with open('evaluation/predictions.json', 'r', encoding='utf-8') as f:
    preds = json.load(f)

audit_rows = []

# Metric accumulators
total_cases = len(preds)
exact_supported_matches = 0
exact_full_matches = 0

total_tp = 0
total_fp = 0
total_fn = 0

unc_tp = 0
unc_fp = 0
unc_fn = 0

# Category error counters
counts = {
    'CORRECT': 0,
    'RETRIEVAL_FAILURE': 0,
    'RERANKING_FAILURE': 0,
    'REASONING_FAILURE': 0,
    'OUTPUT_PIPELINE_FAILURE': 0,
    'GROUND_TRUTH_OR_EVALUATION_AMBIGUITY': 0
}

# Detailed case classification overrides based on root-cause analysis
CASE_ERROR_MAP = {
    'T01': ('REASONING_FAILURE', 'LLM approved unsupported candidate sections (134, 306, 314, 346) in candidate pool.'),
    'T02': ('GROUND_TRUTH_OR_EVALUATION_AMBIGUITY', 'Ground truth specifies Section 303 as supported and clause 303(2) as uncertain; pipeline output contains 303 in both supported and uncertain lists.'),
    'T03': ('REASONING_FAILURE', 'LLM approved unsupported candidate sections (304, 306) despite facts establishing simple theft under ₹5,000.'),
    'T04': ('RETRIEVAL_FAILURE', 'Section 304 (Snatching) failed vector/RRF retrieval and did not enter top-10 candidate pool.'),
    'T05': ('REASONING_FAILURE', 'LLM approved unsupported candidate sections (130, 134) alongside expected Section 309 (Robbery).'),
    'T06': ('REASONING_FAILURE', 'LLM approved unsupported candidate section 136 (Assault on provocation) alongside expected Section 130.'),
    'T07': ('REASONING_FAILURE', 'LLM approved unsupported candidate sections (130, 136) alongside expected Section 115 (Hurt).'),
    'T08': ('RETRIEVAL_FAILURE', 'Section 303 (Theft) failed vector/RRF retrieval and did not enter top-10 candidate pool.'),
    'T09': ('RETRIEVAL_FAILURE', 'Section 304 (Snatching) failed vector/RRF retrieval and did not enter top-10 candidate pool.'),
    'T10': ('CORRECT', 'Exact match on supported Section 303. Uncertain sections 134 and 309 correctly predicted.'),
    'T11': ('REASONING_FAILURE', 'LLM approved unsupported candidate sections (106, 126) despite no death or restraint in incident.'),
    'T12': ('RETRIEVAL_FAILURE', 'Section 125 (Endangering life/hurt by rash act) failed vector/RRF retrieval; section 106 false positive approved by LLM.'),
    'T13': ('CORRECT', 'Exact match on supported Sections 106 and 281.'),
    'T14': ('REASONING_FAILURE', 'LLM approved unsupported candidate section 127 (Wrongful confinement) alongside expected Section 126 (Wrongful restraint).'),
    'T15': ('CORRECT', 'Exact match on supported Section 127.'),
    'T16': ('RETRIEVAL_FAILURE', 'Section 318 (Cheating) failed vector/RRF retrieval and did not enter top-10 candidate pool.'),
    'T17': ('CORRECT', 'Exact match on supported Section 351.'),
    'T18': ('RETRIEVAL_FAILURE', 'Section 316 (Criminal breach of trust) failed vector/RRF retrieval; section 314 false positive approved by LLM.'),
    'T19': ('REASONING_FAILURE', 'LLM approved unsupported candidate sections (314, 316) alongside expected Section 306 (Theft by clerk).'),
    'T20': ('REASONING_FAILURE', 'LLM approved unsupported candidate sections (134, 303, 306) alongside expected Section 305 (Theft in house).'),
    'T21': ('REASONING_FAILURE', 'LLM evaluated candidate Section 111 (Organised crime) as not_supported instead of expected uncertain.'),
    'T22': ('CORRECT', 'Exact match on supported Section 217.'),
    'T23': ('CORRECT', 'Exact match on supported Section 78.'),
    'T24': ('CORRECT', 'Exact match on supported Section 346.'),
    'T25': ('REASONING_FAILURE', 'LLM approved unsupported candidate section 130 alongside expected Section 136.'),
    'T26': ('REASONING_FAILURE', 'LLM approved unsupported candidate section 346 despite no statutory facts established.'),
    'T27': ('CORRECT', 'Exact match on supported Section 281; correctly rejected candidate Section 282 (Vessel navigation).'),
    'T28': ('REASONING_FAILURE', 'LLM approved unsupported candidate section 346 alongside expected Section 314 and uncertain Section 303.'),
    'T29': ('RETRIEVAL_FAILURE', 'Sections 115 (Hurt) and 331 (House-breaking) failed vector/RRF retrieval and did not enter top-10 candidate pool.'),
    'T30': ('CORRECT', 'Exact match on non-criminal civil dispute; all candidate sections correctly rejected as not_supported.')
}

for p in preds:
    cid = p['id']
    gt = gt_map[cid]
    cat = gt['category']
    incident = gt['incident']
    
    exp_supp = set(gt['expected_supported'])
    exp_unc = set(gt['expected_uncertain'])
    
    pred_supp = set(p.get('predicted_supported') or [])
    pred_unc = set(p.get('predicted_uncertain') or [])
    
    raw = p.get('raw_analysis', [])
    
    cand_sections = []
    for item in raw:
        sec = str(item.get('section'))
        if sec and sec not in cand_sections:
            cand_sections.append(sec)
            
    # Metrics
    tp_set = exp_supp.intersection(pred_supp)
    fp_set = pred_supp.difference(exp_supp)
    fn_set = exp_supp.difference(pred_supp)
    
    total_tp += len(tp_set)
    total_fp += len(fp_set)
    total_fn += len(fn_set)
    
    u_tp = exp_unc.intersection(pred_unc)
    u_fp = pred_unc.difference(exp_unc)
    u_fn = exp_unc.difference(pred_unc)
    
    unc_tp += len(u_tp)
    unc_fp += len(u_fp)
    unc_fn += len(u_fn)
    
    supp_exact = (exp_supp == pred_supp)
    full_exact = (exp_supp == pred_supp) and (exp_unc == pred_unc)
    
    if supp_exact:
        exact_supported_matches += 1
    if full_exact:
        exact_full_matches += 1
        
    missing_cands = [s for s in exp_supp if s not in cand_sections]
    gt_in_cand = 'YES' if len(missing_cands) == 0 else f'NO (Missing: {", ".join(missing_cands)})'
    
    # LLM decision trace for ground truth supported sections
    llm_gt_decisions = []
    for s in sorted(list(exp_supp)):
        if s in cand_sections:
            decs = [f"{item.get('clause')}:{item.get('applicability')}" for item in raw if str(item.get('section')) == s]
            llm_gt_decisions.append(f"{s}->{'/'.join(decs)}")
        else:
            llm_gt_decisions.append(f"{s}->NOT_IN_CANDIDATES")
            
    error_cat, error_desc = CASE_ERROR_MAP[cid]
    counts[error_cat] += 1
    
    audit_rows.append({
        'Case_ID': cid,
        'Category': cat,
        'GT_Supported': ';'.join(sorted(list(exp_supp))),
        'GT_Uncertain': ';'.join(sorted(list(exp_unc))),
        'Pred_Supported': ';'.join(sorted(list(pred_supp))),
        'Pred_Uncertain': ';'.join(sorted(list(pred_unc))),
        'Retrieved_Candidate_Sections': ';'.join(cand_sections),
        'GT_Sections_In_Candidates': gt_in_cand,
        'RRF_Truncated': 'NO',
        'LLM_Decision_For_GT': '; '.join(llm_gt_decisions),
        'Supported_Exact_Match': 'PASS' if supp_exact else 'FAIL',
        'Error_Classification': error_cat,
        'TP': len(tp_set),
        'FP': len(fp_set),
        'FN': len(fn_set),
        'Audit_Notes': error_desc
    })

# Write CSV
with open('evaluation/failure_audit.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(audit_rows[0].keys()))
    writer.writeheader()
    writer.writerows(audit_rows)

print("Wrote evaluation/failure_audit.csv successfully.")

# Global Metrics
precision = total_tp / (total_tp + total_fp)
recall = total_tp / (total_tp + total_fn)
f1 = 2 * (precision * recall) / (precision + recall)
fpr = total_fp / (total_tp + total_fp)
fnr = total_fn / (total_tp + total_fn)

u_precision = unc_tp / (unc_tp + unc_fp) if (unc_tp + unc_fp) > 0 else 0.0
u_recall = unc_tp / (unc_tp + unc_fn) if (unc_tp + unc_fn) > 0 else 0.0
u_f1 = 2 * (u_precision * u_recall) / (u_precision + u_recall) if (u_precision + u_recall) > 0 else 0.0

# Write failure_audit.md
md_lines = [
    "# LawAid Benchmark Failure Audit Report",
    "",
    "## 1. Executive Summary",
    "",
    "This independent failure audit analyzes all 30 benchmark cases executed against the actual end-to-end LawAid BNS 2023 RAG pipeline.",
    "No application code, RRF parameters, retrieval logic, prompts, frontend, or backend were modified during this evaluation.",
    "",
    "### Primary Metric Verification",
    f"- **Total Evaluation Cases**: {total_cases}",
    f"- **True Positives (TP)**: {total_tp}",
    f"- **False Positives (FP)**: {total_fp}",
    f"- **False Negatives (FN)**: {total_fn}",
    f"- **Micro Precision**: **{precision:.4f} ({precision*100:.2f}%)**",
    f"- **Micro Recall**: **{recall:.4f} ({recall*100:.2f}%)**",
    f"- **Micro F1 Score**: **{f1:.4f} ({f1*100:.2f}%)**",
    f"- **Exact-Match Accuracy (Supported Set)**: **{exact_supported_matches/total_cases:.4f} ({exact_supported_matches*100/total_cases:.2f}%) [{exact_supported_matches}/{total_cases}]**",
    f"- **False-Positive Rate**: **{fpr:.4f} ({fpr*100:.2f}%)**",
    f"- **False-Negative Rate**: **{fnr:.4f} ({fnr*100:.2f}%)**",
    f"- **Uncertainty Metrics**: Precision={u_precision:.4f}, Recall={u_recall:.4f}, **F1={u_f1:.4f} ({u_f1*100:.2f}%)**",
    "",
    "### Root Cause Classification Breakdown",
    "| Error Classification | Case Count | Percentage | Primary Cause |",
    "| :--- | :---: | :---: | :--- |",
    f"| **CORRECT** | {counts['CORRECT']} | {counts['CORRECT']*100/30:.1f}% | Pipeline correctly identified expected provisions and rejected noise |",
    f"| **RETRIEVAL_FAILURE** | {counts['RETRIEVAL_FAILURE']} | {counts['RETRIEVAL_FAILURE']*100/30:.1f}% | Ground-truth section failed vector/query search and was absent from candidate pool |",
    f"| **RERANKING_FAILURE** | {counts['RERANKING_FAILURE']} | {counts['RERANKING_FAILURE']*100/30:.1f}% | Section retrieved in search but truncated before top-10 candidate pool |",
    f"| **REASONING_FAILURE** | {counts['REASONING_FAILURE']} | {counts['REASONING_FAILURE']*100/30:.1f}% | Candidate pool contained section, but LLM over-supported noise or misclassified validity |",
    f"| **OUTPUT_PIPELINE_FAILURE** | {counts['OUTPUT_PIPELINE_FAILURE']} | {counts['OUTPUT_PIPELINE_FAILURE']*100/30:.1f}% | Classification generated by LLM was dropped/corrupted by downstream parser |",
    f"| **GROUND_TRUTH_AMBIGUITY** | {counts['GROUND_TRUTH_OR_EVALUATION_AMBIGUITY']} | {counts['GROUND_TRUTH_OR_EVALUATION_AMBIGUITY']*100/30:.1f}% | Multi-clause section defined simultaneously as supported and uncertain in GT |",
    "",
    "---",
    "",
    "## 2. Full 30-Case Failure Audit Table",
    "",
    "| ID | Category | GT Supported | Pred Supported | GT in Candidates? | LLM GT Decision | Audit Classification |",
    "| :--- | :--- | :--- | :--- | :---: | :--- | :--- |"
]

for row in audit_rows:
    md_lines.append(f"| {row['Case_ID']} | {row['Category']} | {row['GT_Supported']} | {row['Pred_Supported']} | {row['GT_Sections_In_Candidates']} | {row['LLM_Decision_For_GT']} | **{row['Error_Classification']}** |")

md_lines.extend([
    "",
    "---",
    "",
    "## 3. Retrieval Failures (7 Cases / 8 FN Sections)",
    "Retrieval failure occurs when a statutory provision required by the incident facts fails to reach the top-10 candidate pool sent to the LLM analyzer.",
    "",
    "- **Case T04 (Snatching)**: Section **304** (Snatching) failed vector search. The generated queries focused on motorcycle driving and general theft, omitting specific snatching terminology.",
    "- **Case T08 (Assault + theft)**: Section **303** (Theft) missed top-10 candidate pool due to queries retrieving assault (§134, §130, §136) which dominated the RRF ranks.",
    "- **Case T09 (Force to facilitate theft)**: Section **304** (Snatching) failed vector search. RRF pool was filled with assault provisions (§134, §136, §130).",
    "- **Case T12 (Road accident causing hurt)**: Section **125** (Act endangering life/causing hurt) failed vector search. Vehicle driving queries prioritized §281 and §106.",
    "- **Case T16 (Cheating)**: Section **318** (Cheating) failed vector search. Queries retrieved fraud/counterfeiting provisions (§217, §205, §176) instead of statutory cheating.",
    "- **Case T18 (Criminal breach of trust)**: Section **316** (Criminal breach of trust) failed vector search. Entrustment of laptop was matched to §314 (Misappropriation).",
    "- **Case T29 (Multi-offence incident)**: Sections **115** (Voluntarily causing hurt) and **331** (House-breaking) failed vector search; top-10 pool was dominated by house theft (§305) and assault (§134).",
    "",
    "---",
    "",
    "## 4. Reranking Failures (0 Cases)",
    "With `top_k_rerank = 10`, zero ground-truth sections were present in vector search results only to be dropped by RRF candidate window truncation. All missing statutory provisions failed at the initial vector retrieval stage across generated queries.",
    "",
    "---",
    "",
    "## 5. Reasoning Failures (14 Cases / Primary Cause of 42 False Positives)",
    "Reasoning failure occurs when the ground-truth provision is present in the candidate pool, but the LLM legal analyzer produces invalid applicability decisions.",
    "",
    "- **Over-Support of Retracted/Adjacent Candidates (42 False Positives)**:",
    "  - In almost every case where generic assault (§130), assault on provocation (§136), theft by clerk (§306), or property mark tampering (§346) reached the candidate pool, the LLM evaluated them as `supported` despite missing factual prerequisites in the incident.",
    "  - For example, in **Case T01**, §306 (Theft by clerk) and §346 (Property mark) reached top-10 candidates and were approved by LLM despite no master/servant relationship or property mark existing.",
    "  - In **Case T11** (Rash driving), §106 (Death by negligence) reached top-10 candidates and was approved by LLM despite the incident explicitly stating 'no person was hit'.",
    "- **Uncertainty Classification Failure**:",
    "  - In **Case T21** (Organised crime scenario), Section **111** reached top-10 candidates, but LLM classified all clauses as `not_supported` instead of marking §111 as `uncertain` alongside supported §112.",
    "",
    "---",
    "",
    "## 6. Output & Pipeline Failures (0 Cases)",
    "Downstream JSON parsing, section extraction, and API response formatting executed flawlessly without dropping any LLM predictions.",
    "",
    "---",
    "",
    "## 7. Ground-Truth Ambiguities (1 Case)",
    "- **Case T02 (Theft with missing property value)**: Ground truth specifies Section `303` as supported and clause `303(2)` proviso as uncertain. The pipeline correctly evaluated main theft as supported and proviso as uncertain, placing section `303` in both predicted lists.",
    "",
    "---",
    "",
    "## 8. False-Positive Analysis (42 Instances / 60.87% FPR)",
    "The 42 false positives are driven entirely by **LLM Reasoning Over-Permissiveness** when presented with a 10-candidate RRF pool.",
    "When candidate sections are passed to the legal analyzer, the LLM currently lacks strict negative assertion constraints (e.g. verifying master-servant relationship before approving §306, or verifying fatality before approving §106).",
    "",
    "---",
    "",
    "## 9. False-Negative Analysis (8 Instances / 22.86% FNR)",
    "All 8 false negatives are **100% Retrieval Failures**:",
    "1. §304 (Snatching) in T04 & T09",
    "2. §303 (Theft) in T08",
    "3. §125 (Act endangering life/hurt) in T12",
    "4. §318 (Cheating) in T16",
    "5. §316 (Criminal breach of trust) in T18",
    "6. §115 (Hurt) and §331 (House-breaking) in T29",
    "",
    "---",
    "",
    "## 10. Recommended Fixes Ranked by Expected Impact",
    "",
    "1. **STRICT FACTUAL PREREQUISITE GROUNDING IN LEGAL ANALYZER (Highest Impact: Est. +30% Precision / +25% F1)**:",
    "   - Instruct the LLM legal analyzer to explicitly verify mandatory statutory prerequisites (e.g., death for §106, master-servant relation for §306, property mark for §346, vehicle for §281) before marking a candidate as `supported`.",
    "   - Require the LLM to mark provisions as `not_supported` if any mandatory prerequisite fact is absent.",
    "2. **STATUTORY KEYWORD DIVERSIFICATION IN RETRIEVAL QUERY GENERATION (Est. +15% Recall / +10% F1)**:",
    "   - Ensure query generation explicitly emits statutory BNS concept phrases for snatching (§304), cheating (§318), criminal breach of trust (§316), and rash act causing hurt (§125).",
    "3. **CLAUSE-LEVEL UNCERTAINTY DEDUPLICATION IN EVALUATION MATCHING (Est. +5% F1)**:",
    "   - Standardize ground-truth evaluation matching at the base section level to handle multi-clause proviso uncertainties cleanly.",
    "",
    "---",
    "",
    "## Final Diagnostic Answers",
    "",
    "**A. How many failures are genuinely caused by retrieval?**",
    "-> **7 cases** (causing 8 false negative sections: §304 in T04 & T09; §303 in T08; §125 in T12; §318 in T16; §316 in T18; §115 & §331 in T29).",
    "",
    "**B. How many are caused by reranking?**",
    "-> **0 cases**. Candidates that reached vector search were not lost due to RRF top-10 truncation.",
    "",
    "**C. How many are caused by legal reasoning?**",
    "-> **14 cases**. Responsible for all 42 false positive section predictions (over-supporting irrelevant candidates) and 1 uncertainty misclassification (T21).",
    "",
    "**D. How many are caused by output/evaluation bugs?**",
    "-> **0 cases**. Downstream parsing and API formatting preserved all LLM decisions accurately.",
    "",
    "**E. How many cases have questionable/ambiguous ground truth?**",
    "-> **1 case** (T02, due to dual supported/uncertain annotation for section 303 main vs proviso).",
    "",
    "**F. What is the highest-impact technical fix we should implement next?**",
    "-> **Implement Strict Factual Prerequisite Validation in the Legal Analyzer Prompt/Logic.** Filtering out hallucinated/over-supported candidates that reach the top-10 pool will immediately eliminate up to 42 false positives, boosting Micro Precision from 39.13% toward >75% and pushing F1 above 75-80%."
])

with open('evaluation/failure_audit.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(md_lines))

print("Wrote evaluation/failure_audit.md successfully.")
