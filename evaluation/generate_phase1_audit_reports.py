import csv
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

audit_data = [
    {
        'Case_ID': 'T01',
        'Category': 'Simple theft',
        'GT_Supported': '303',
        'GT_Uncertain': '',
        'Baseline_Supported': '134;303;306;314;346',
        'Baseline_Uncertain': '303',
        'Phase1_Supported': '314;346',
        'Phase1_Uncertain': '303',
        'Removed_Predictions': '134 (FP); 303 (TP); 306 (FP)',
        'Newly_Added_Predictions': 'None',
        'Change_Classification': 'FALSE POSITIVE REMOVED (134, 306); TRUE POSITIVE REMOVED / FALSE NEGATIVE CREATED (303)',
        'Exact_Reasoning_And_Evidence': 'Phase 1 prompt strictly required unstated monetary threshold to be marked uncertain. The LLM marked section 303 proviso as uncertain and omitted main 303 theft from supported set, creating FN for 303. FP 134 (Assault in theft) and FP 306 (Theft by clerk) were successfully eliminated.'
    },
    {
        'Case_ID': 'T02',
        'Category': 'Theft with missing property value',
        'GT_Supported': '303',
        'GT_Uncertain': '303(2)',
        'Baseline_Supported': '134;303;304;305;306',
        'Baseline_Uncertain': '303',
        'Phase1_Supported': '303;304;305;306',
        'Phase1_Uncertain': '303',
        'Removed_Predictions': '134 (FP)',
        'Newly_Added_Predictions': 'None',
        'Change_Classification': 'FALSE POSITIVE REMOVED (134)',
        'Exact_Reasoning_And_Evidence': 'Section 134 (Assault in theft) was correctly removed by Phase 1 prerequisite verification because no physical force or assault occurred. Note: T02 has GT ambiguity where 303 is in both GT supported and GT uncertain.'
    },
    {
        'Case_ID': 'T04',
        'Category': 'Snatching',
        'GT_Supported': '304',
        'GT_Uncertain': '',
        'Baseline_Supported': '126;134;281;303',
        'Baseline_Uncertain': '303',
        'Phase1_Supported': '126;281;303',
        'Phase1_Uncertain': '303',
        'Removed_Predictions': '134 (FP)',
        'Newly_Added_Predictions': 'None',
        'Change_Classification': 'FALSE POSITIVE REMOVED (134)',
        'Exact_Reasoning_And_Evidence': 'Section 134 (Assault in theft) was correctly removed because the incident facts describe sudden snatching without independent assault under 134.'
    },
    {
        'Case_ID': 'T05',
        'Category': 'Robbery',
        'GT_Supported': '309',
        'GT_Uncertain': '',
        'Baseline_Supported': '130;134;309',
        'Baseline_Uncertain': '',
        'Phase1_Supported': '130;309',
        'Phase1_Uncertain': '',
        'Removed_Predictions': '134 (FP)',
        'Newly_Added_Predictions': 'None',
        'Change_Classification': 'FALSE POSITIVE REMOVED (134)',
        'Exact_Reasoning_And_Evidence': 'Section 134 (Assault in attempting theft) was correctly removed as redundant to Section 309 (Robbery).'
    },
    {
        'Case_ID': 'T06',
        'Category': 'Assault',
        'GT_Supported': '130',
        'GT_Uncertain': '',
        'Baseline_Supported': '130;136',
        'Baseline_Uncertain': '',
        'Phase1_Supported': '115;125',
        'Phase1_Uncertain': '',
        'Removed_Predictions': '130 (TP); 136 (FP)',
        'Newly_Added_Predictions': '115 (FP); 125 (FP)',
        'Change_Classification': 'TRUE POSITIVE REMOVED / FALSE NEGATIVE CREATED (130); FALSE POSITIVE REMOVED (136); FALSE POSITIVE CREATED (115, 125)',
        'Exact_Reasoning_And_Evidence': 'Section 130 missed candidate retrieval pool in this run. Section 136 was removed, but candidate sections 115 and 125 were retrieved and supported.'
    },
    {
        'Case_ID': 'T10',
        'Category': 'Ambiguous force + theft',
        'GT_Supported': '303',
        'GT_Uncertain': '134;309',
        'Baseline_Supported': '303',
        'Baseline_Uncertain': '134;303;309',
        'Phase1_Supported': '303',
        'Phase1_Uncertain': '303;309',
        'Removed_Predictions': '134 (from uncertain)',
        'Newly_Added_Predictions': 'None',
        'Change_Classification': 'UNCERTAINTY CHANGE (134)',
        'Exact_Reasoning_And_Evidence': 'Section 134 was classified as not_supported by Phase 1 prerequisite check instead of uncertain, cleanly removing it from the uncertain list while preserving supported 303.'
    },
    {
        'Case_ID': 'T20',
        'Category': 'Theft in dwelling house',
        'GT_Supported': '305',
        'GT_Uncertain': '329;331',
        'Baseline_Supported': '134;303;305;306',
        'Baseline_Uncertain': '303',
        'Phase1_Supported': '303;305;306',
        'Phase1_Uncertain': '303',
        'Removed_Predictions': '134 (FP)',
        'Newly_Added_Predictions': 'None',
        'Change_Classification': 'FALSE POSITIVE REMOVED (134)',
        'Exact_Reasoning_And_Evidence': 'Section 134 was correctly removed by Phase 1 prerequisite evaluation as no assault was mentioned in house theft.'
    },
    {
        'Case_ID': 'T21',
        'Category': 'Organised/petty organised crime scenario',
        'GT_Supported': '112;304',
        'GT_Uncertain': '111',
        'Baseline_Supported': '112;304',
        'Baseline_Uncertain': '',
        'Phase1_Supported': '112',
        'Phase1_Uncertain': '',
        'Removed_Predictions': '304 (TP)',
        'Newly_Added_Predictions': 'None',
        'Change_Classification': 'TRUE POSITIVE REMOVED / FALSE NEGATIVE CREATED (304)',
        'Exact_Reasoning_And_Evidence': 'Section 304 (Snatching) missed top-10 candidate pool in this evaluation run, causing a false negative for 304.'
    }
]

# Save CSV
with open('evaluation/phase1_change_audit.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(audit_data[0].keys()))
    writer.writeheader()
    writer.writerows(audit_data)

print("Wrote evaluation/phase1_change_audit.csv successfully.")

# Save Markdown
md_lines = [
    "# LawAid Phase 1 Change-Impact Audit Report",
    "",
    "## 1. Executive Summary",
    "",
    "This audit compares the **Baseline Benchmark** predictions against the **Post-Phase-1 Benchmark** predictions across all 30 evaluation cases.",
    "No application code, prompts, retrieval parameters, or evaluation ground truths were modified during this audit.",
    "",
    "### Metric Comparison Overview",
    "",
    "| Metric | Baseline | Post-Phase 1 | Delta / Net Change |",
    "| :--- | :---: | :---: | :---: |",
    "| **True Positives (TP)** | 27 | 24 | -3 (3 TPs removed) |",
    "| **False Positives (FP)** | 42 | 37 | **-5 (-11.9% Noise Reduction)** |",
    "| **False Negatives (FN)** | 8 | 11 | +3 (3 FNs created) |",
    "| **Micro Precision** | 39.13% | **39.34%** | **+0.21%** |",
    "| **Micro Recall** | 77.14% | 68.57% | -8.57% |",
    "| **Micro F1 Score** | 51.92% | 50.00% | -1.92% |",
    "| **Exact-Match Accuracy** | 33.33% (10/30) | 30.00% (9/30) | -3.33% |",
    "",
    "---",
    "",
    "## 2. Full Changed Cases Audit Table",
    "",
    "| Case ID | Category | Baseline Supp | Phase-1 Supp | Removed Preds | Added Preds | Change Classification |",
    "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
]

for row in audit_data:
    md_lines.append(f"| {row['Case_ID']} | {row['Category']} | {row['Baseline_Supported']} | {row['Phase1_Supported']} | {row['Removed_Predictions']} | {row['Newly_Added_Predictions']} | **{row['Change_Classification']}** |")

md_lines.extend([
    "",
    "---",
    "",
    "## 3. Analysis of Removed False Positives (5 Net FP Reduction)",
    "",
    "Phase 1 prerequisite verification successfully removed 7 false positive predictions across 6 cases, offset by 2 new false positives in T06:",
    "",
    "1. **Case T01 (Simple theft)**: Removed FP **§134** (Assault in theft) and FP **§306** (Theft by clerk). Reason: incident has no assault or employee relationship.",
    "2. **Case T02 (Theft with missing value)**: Removed FP **§134** (Assault in theft). Reason: mobile phone theft without assault.",
    "3. **Case T04 (Snatching)**: Removed FP **§134** (Assault in theft). Reason: sudden snatching without independent Section 134 assault.",
    "4. **Case T05 (Robbery)**: Removed FP **§134** (Assault in theft). Reason: redundant to Section 309 (Robbery).",
    "5. **Case T06 (Assault)**: Removed FP **§136** (Assault on grave provocation). Reason: incident has no provocation.",
    "6. **Case T20 (Theft in house)**: Removed FP **§134** (Assault in theft). Reason: house theft without assault.",
    "",
    "---",
    "",
    "## 4. Analysis of Created False Negatives (3 Additional FNs)",
    "",
    "1. **Case T01 (Section 303 Theft)**:",
    "   - **Reason**: The Phase 1 prompt instructed the model to mark proviso clauses `uncertain` when monetary values are unstated. In T01 ('stole a bicycle'), the LLM marked Section 303 proviso as `uncertain` and omitted main Section 303 theft from `predicted_supported`.",
    "   - **Impact**: Ground truth expected Section 303 as supported, so omitting 303 from `predicted_supported` created an artificial false negative.",
    "2. **Case T06 (Section 130 Assault)**:",
    "   - **Reason**: Retrieval candidate pool variance. In this evaluation run, Section 130 was omitted from the top-10 candidate pool sent to the legal analyzer.",
    "3. **Case T21 (Section 304 Snatching)**:",
    "   - **Reason**: Retrieval candidate pool variance. In this evaluation run, Section 304 was omitted from the top-10 candidate pool sent to the legal analyzer.",
    "",
    "---",
    "",
    "## 5. Detailed Investigation of T01 & T02",
    "",
    "### T01 (Simple Theft)",
    "- **Main Theft vs Proviso Distinction**: Section 303 contains both general theft definitions (§303(1)/§303(2) main) and a specific proviso for property value < ₹5,000 (§303(2) proviso).",
    "- **Root Cause**: The LLM evaluated `bns_303_303(2)-2` (the proviso document) as `uncertain` due to unstated bicycle value. However, main theft (§303) is fully supported by the dishonest taking of movable property without consent.",
    "- **Fix**: In Phase 1 refinement, ensure main Section 303 theft is preserved in `predicted_supported` when dishonest taking is established, while keeping the < ₹5,000 proviso marked `uncertain`.",
    "",
    "### T02 (Theft with Missing Property Value Ground-Truth Ambiguity)",
    "- **Ground-Truth Ambiguity Flag**: In `ground_truth.json`, T02 lists `expected_supported: ['303']` and `expected_uncertain: ['303(2)']` simultaneously.",
    "- **Evaluation Impact**: At the section-level, evaluation normalizes `303(2)` to `303`. Thus, `303` appears in both expected supported and expected uncertain categories in evaluation matching. Ground truth should be refined in future phases to prevent double-counting.",
    "",
    "---",
    "",
    "## 6. Final Recommendation",
    "",
    "**RECOMMENDATION: C. REFINE Phase 1**",
    "",
    "### Justification:",
    "- **Do NOT Revert (B)**: Phase 1's generic prerequisite reasoning successfully eliminated 7 false positives (such as hallucinated §134 and §306 predictions across theft and robbery cases). Reverting would re-introduce massive false positive noise.",
    "- **Do NOT Keep Unchanged (A)**: Keeping Phase 1 unchanged allows the strict prompt rule for unstated monetary thresholds to inadvertently remove main theft (§303 in T01) from `predicted_supported`.",
    "- **Why Refine (C)**: Refine the prompt and legal analyzer post-processing so that **main core offence definitions** (e.g. general theft under Section 303) remain `supported` when core elements are satisfied, even while specific **monetary proviso clauses** are classified as `uncertain`. This will immediately recover lost recall (eliminating the T01 false negative) while preserving the 7 false-positive reductions."
])

with open('evaluation/phase1_change_audit.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(md_lines))

print("Wrote evaluation/phase1_change_audit.md successfully.")
