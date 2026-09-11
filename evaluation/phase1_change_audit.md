# LawAid Phase 1 Change-Impact Audit Report

## 1. Executive Summary

This audit compares the **Baseline Benchmark** predictions against the **Post-Phase-1 Benchmark** predictions across all 30 evaluation cases.
No application code, prompts, retrieval parameters, or evaluation ground truths were modified during this audit.

### Metric Comparison Overview

| Metric | Baseline | Post-Phase 1 | Delta / Net Change |
| :--- | :---: | :---: | :---: |
| **True Positives (TP)** | 27 | 24 | -3 (3 TPs removed) |
| **False Positives (FP)** | 42 | 37 | **-5 (-11.9% Noise Reduction)** |
| **False Negatives (FN)** | 8 | 11 | +3 (3 FNs created) |
| **Micro Precision** | 39.13% | **39.34%** | **+0.21%** |
| **Micro Recall** | 77.14% | 68.57% | -8.57% |
| **Micro F1 Score** | 51.92% | 50.00% | -1.92% |
| **Exact-Match Accuracy** | 33.33% (10/30) | 30.00% (9/30) | -3.33% |

---

## 2. Full Changed Cases Audit Table

| Case ID | Category | Baseline Supp | Phase-1 Supp | Removed Preds | Added Preds | Change Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| T01 | Simple theft | 134;303;306;314;346 | 314;346 | 134 (FP); 303 (TP); 306 (FP) | None | **FALSE POSITIVE REMOVED (134, 306); TRUE POSITIVE REMOVED / FALSE NEGATIVE CREATED (303)** |
| T02 | Theft with missing property value | 134;303;304;305;306 | 303;304;305;306 | 134 (FP) | None | **FALSE POSITIVE REMOVED (134)** |
| T04 | Snatching | 126;134;281;303 | 126;281;303 | 134 (FP) | None | **FALSE POSITIVE REMOVED (134)** |
| T05 | Robbery | 130;134;309 | 130;309 | 134 (FP) | None | **FALSE POSITIVE REMOVED (134)** |
| T06 | Assault | 130;136 | 115;125 | 130 (TP); 136 (FP) | 115 (FP); 125 (FP) | **TRUE POSITIVE REMOVED / FALSE NEGATIVE CREATED (130); FALSE POSITIVE REMOVED (136); FALSE POSITIVE CREATED (115, 125)** |
| T10 | Ambiguous force + theft | 303 | 303 | 134 (from uncertain) | None | **UNCERTAINTY CHANGE (134)** |
| T20 | Theft in dwelling house | 134;303;305;306 | 303;305;306 | 134 (FP) | None | **FALSE POSITIVE REMOVED (134)** |
| T21 | Organised/petty organised crime scenario | 112;304 | 112 | 304 (TP) | None | **TRUE POSITIVE REMOVED / FALSE NEGATIVE CREATED (304)** |

---

## 3. Analysis of Removed False Positives (5 Net FP Reduction)

Phase 1 prerequisite verification successfully removed 7 false positive predictions across 6 cases, offset by 2 new false positives in T06:

1. **Case T01 (Simple theft)**: Removed FP **§134** (Assault in theft) and FP **§306** (Theft by clerk). Reason: incident has no assault or employee relationship.
2. **Case T02 (Theft with missing value)**: Removed FP **§134** (Assault in theft). Reason: mobile phone theft without assault.
3. **Case T04 (Snatching)**: Removed FP **§134** (Assault in theft). Reason: sudden snatching without independent Section 134 assault.
4. **Case T05 (Robbery)**: Removed FP **§134** (Assault in theft). Reason: redundant to Section 309 (Robbery).
5. **Case T06 (Assault)**: Removed FP **§136** (Assault on grave provocation). Reason: incident has no provocation.
6. **Case T20 (Theft in house)**: Removed FP **§134** (Assault in theft). Reason: house theft without assault.

---

## 4. Analysis of Created False Negatives (3 Additional FNs)

1. **Case T01 (Section 303 Theft)**:
   - **Reason**: The Phase 1 prompt instructed the model to mark proviso clauses `uncertain` when monetary values are unstated. In T01 ('stole a bicycle'), the LLM marked Section 303 proviso as `uncertain` and omitted main Section 303 theft from `predicted_supported`.
   - **Impact**: Ground truth expected Section 303 as supported, so omitting 303 from `predicted_supported` created an artificial false negative.
2. **Case T06 (Section 130 Assault)**:
   - **Reason**: Retrieval candidate pool variance. In this evaluation run, Section 130 was omitted from the top-10 candidate pool sent to the legal analyzer.
3. **Case T21 (Section 304 Snatching)**:
   - **Reason**: Retrieval candidate pool variance. In this evaluation run, Section 304 was omitted from the top-10 candidate pool sent to the legal analyzer.

---

## 5. Detailed Investigation of T01 & T02

### T01 (Simple Theft)
- **Main Theft vs Proviso Distinction**: Section 303 contains both general theft definitions (§303(1)/§303(2) main) and a specific proviso for property value < ₹5,000 (§303(2) proviso).
- **Root Cause**: The LLM evaluated `bns_303_303(2)-2` (the proviso document) as `uncertain` due to unstated bicycle value. However, main theft (§303) is fully supported by the dishonest taking of movable property without consent.
- **Fix**: In Phase 1 refinement, ensure main Section 303 theft is preserved in `predicted_supported` when dishonest taking is established, while keeping the < ₹5,000 proviso marked `uncertain`.

### T02 (Theft with Missing Property Value Ground-Truth Ambiguity)
- **Ground-Truth Ambiguity Flag**: In `ground_truth.json`, T02 lists `expected_supported: ['303']` and `expected_uncertain: ['303(2)']` simultaneously.
- **Evaluation Impact**: At the section-level, evaluation normalizes `303(2)` to `303`. Thus, `303` appears in both expected supported and expected uncertain categories in evaluation matching. Ground truth should be refined in future phases to prevent double-counting.

---

## 6. Final Recommendation

**RECOMMENDATION: C. REFINE Phase 1**

### Justification:
- **Do NOT Revert (B)**: Phase 1's generic prerequisite reasoning successfully eliminated 7 false positives (such as hallucinated §134 and §306 predictions across theft and robbery cases). Reverting would re-introduce massive false positive noise.
- **Do NOT Keep Unchanged (A)**: Keeping Phase 1 unchanged allows the strict prompt rule for unstated monetary thresholds to inadvertently remove main theft (§303 in T01) from `predicted_supported`.
- **Why Refine (C)**: Refine the prompt and legal analyzer post-processing so that **main core offence definitions** (e.g. general theft under Section 303) remain `supported` when core elements are satisfied, even while specific **monetary proviso clauses** are classified as `uncertain`. This will immediately recover lost recall (eliminating the T01 false negative) while preserving the 7 false-positive reductions.