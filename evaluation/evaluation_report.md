# LawAid AI Legal Accuracy Evaluation Report

**Total Benchmark Cases**: 30
**Evaluation Methodology**: End-to-end BNS 2023 RAG Pipeline evaluation over 30 independent statutory cases.

## 1. Executive Summary Metrics

| Metric | Value |
| :--- | :---: |
| **True Positives (TP)** | 28 |
| **False Positives (FP)** | 6 |
| **False Negatives (FN)** | 7 |
| **Precision (Micro)** | 0.8235 (82.35%) |
| **Recall (Micro)** | 0.8000 (80.00%) |
| **F1 Score (Micro)** | 0.8116 (81.16%) |
| **Exact-Match Accuracy** | 0.6333 (63.33%) [19/30] |
| **False-Positive Rate** | 0.1765 (17.65%) |
| **False-Negative Rate** | 0.2000 (20.00%) |
| **Uncertainty F1 Score** | 0.2857 (28.57%) |

## 2. Category Performance Breakdown

| Category | Total Cases | Exact Matches | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Simple theft | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Theft with missing property value | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Theft explicitly below ₹5,000 | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Voluntarily causing hurt | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Ambiguous force + theft | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Rash driving on public road | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Road accident with death | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Wrongful confinement | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Criminal intimidation | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Criminal breach/misappropriation of property | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Theft by employee/clerk | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Organised/petty organised crime scenario | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| False information to public servant | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| A sexual-offence-related case | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| A property-mark offence | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| A case designed to trigger a likely retrieval false positive | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| Another ambiguous case | 1 | 1 | 100.0% | 100.0% | **100.0%** |
| A multi-offence incident | 1 | 0 | 75.0% | 100.0% | **85.7%** |
| Assault + theft | 1 | 0 | 66.7% | 100.0% | **80.0%** |
| Force used specifically to facilitate theft | 1 | 0 | 66.7% | 100.0% | **80.0%** |
| A case involving grave/sudden provocation | 1 | 0 | 50.0% | 100.0% | **66.7%** |
| Road accident causing hurt | 1 | 0 | 50.0% | 50.0% | **50.0%** |
| Snatching | 1 | 0 | 0.0% | 0.0% | **0.0%** |
| Robbery | 1 | 0 | 0.0% | 0.0% | **0.0%** |
| Assault | 1 | 0 | 0.0% | 0.0% | **0.0%** |
| Wrongful restraint | 1 | 0 | 0.0% | 0.0% | **0.0%** |
| Cheating | 1 | 0 | 0.0% | 0.0% | **0.0%** |
| Theft in dwelling house | 1 | 0 | 0.0% | 0.0% | **0.0%** |
| A case where important statutory facts are missing | 1 | 1 | 0.0% | 0.0% | **0.0%** |
| A completely unrelated/non-criminal incident | 1 | 1 | 0.0% | 0.0% | **0.0%** |

## 3. Error & Failure Diagnostic Analysis

- **Retrieval Failures**: 7 instances (expected section not present in candidate pool).
  - Case T04 (Snatching): Section 304 failed retrieval.
  - Case T05 (Robbery): Section 309 failed retrieval.
  - Case T06 (Assault): Section 130 failed retrieval.
  - Case T12 (Road accident causing hurt): Section 125 failed retrieval.
  - Case T14 (Wrongful restraint): Section 126 failed retrieval.
  - Case T16 (Cheating): Section 318 failed retrieval.
  - Case T20 (Theft in dwelling house): Section 305 failed retrieval.
- **Legal Reasoning Failures**: 0 instances (section retrieved but rejected or missed by LLM).
- **Missing-Fact Handling Failures**: 3 instances.
  - Case T20 (Theft in dwelling house): Expected uncertainty for ['331', '329'] missed.
  - Case T21 (Organised/petty organised crime scenario): Expected uncertainty for ['111'] missed.
  - Case T28 (Another ambiguous case): Expected uncertainty for ['303'] missed.

## 4. Final Verdict

**VERDICT: NOT YET FULLY SUPPORTED** — LawAid achieves an F1 score of **81.16%** and Exact-Match Accuracy of **63.33%**. Specific category recall or retrieval gaps require further targeted improvements.
