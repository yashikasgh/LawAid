"""compare_baseline_vs_ner.py — Diagnostic experiment comparing Full Incident Retrieval (Approach A) vs NER-Driven Retrieval (Approach B).

Located at: ai/rag/retrieval/compare_baseline_vs_ner.py
"""

import json
import sys
from pathlib import Path

# Add project root (LawAid) to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add retrieval & ner directories to sys.path
RETRIEVAL_DIR = Path(__file__).resolve().parent
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

NER_DIR = PROJECT_ROOT / "ai" / "rag" / "ner"
if str(NER_DIR) not in sys.path:
    sys.path.insert(0, str(NER_DIR))

from ner_extractor import extract_entities
from retrieve_bns import retrieve
from build_retrieval_query import retrieve_by_ner, build_retrieval_queries


EXAMPLES = [
    {
        "id": "ex1",
        "title": "Example 1 — Snatching / Theft Incident",
        "text": "Yesterday evening around 8 PM near Karol Bagh market, Ramesh was walking home when two unidentified men on a motorcycle snatched his gold chain and fled towards Patel Nagar.",
        "expected_sections": {
            "theft": {
                "section": 304,
                "reason": "The incident describes forcible snatching of a gold chain from a victim on a road. Under BNS 2023, snatching is specifically governed by Section 304 (Snatching), which is distinct from generic theft under Section 303."
            }
        }
    },
    {
        "id": "ex2",
        "title": "Example 2 — Criminal Intimidation & Criminal Trespass",
        "text": "Sub-Inspector Sharma recorded that the accused Sunil illegally entered the shop in Chandni Chowk and threatened to kill the shopkeeper Vijay if he called the police.",
        "expected_sections": {
            "criminal trespass": {
                "section": 329,
                "reason": "Illegal entry into a shop constitutes criminal trespass / house-trespass under BNS Section 329."
            },
            "criminal intimidation": {
                "section": 351,
                "reason": "Threatening to kill a shopkeeper constitutes criminal intimidation under BNS Section 351."
            }
        }
    },
    {
        "id": "ex3",
        "title": "Example 3 — Financial Fraud / Cheating Incident",
        "text": "A complaint was lodged stating that Vijay defrauded several investors of 50 Lakhs through a fake real estate scheme in Noida.",
        "expected_sections": {
            "cheating": {
                "section": 318,
                "reason": "Defrauding investors through a fake real estate scheme constitutes cheating and dishonest inducement under BNS Section 318."
            }
        }
    }
]


def print_top_k_results(results_list, header_title="Top-K Results"):
    print(f"\n  {header_title}:")
    print(f"  {'Rank':<5} | {'Doc ID':<18} | {'Sec':<5} | {'Clause':<8} | {'Distance':<10} | {'Title'}")
    print("  " + "-" * 75)
    for item in results_list:
        rank = item["rank"]
        doc_id = item["id"]
        sec = item["section"]
        cls_disp = item["clause"] if item.get("clause") else "-"
        dist = item["distance"]
        title = item["title"]
        print(f"  {rank:<5} | {doc_id:<18} | {str(sec):<5} | {cls_disp:<8} | {dist:<10.4f} | {title}")


def run_diagnostic_comparison():
    print("=" * 90)
    print("DIAGNOSTIC COMPARISON EXPERIMENT: APPROACH A (FULL NARRATIVE) VS APPROACH B (NER-DRIVEN)")
    print("=" * 90)

    for ex in EXAMPLES:
        print(f"\n==========================================================================================")
        print(f"INCIDENT: {ex['title']}")
        print(f"==========================================================================================")
        print(f"Raw Narrative Text:\n\"{ex['text']}\"\n")

        # 1. Run NER Extraction
        ner_out = extract_entities(ex["text"])
        print("--- [1. NER Extracted Output] ---")
        print(json.dumps(ner_out, indent=2))

        # 2. Approach A: Full Narrative Retrieval
        print("\n--- [2. Approach A: Full Incident Text Retrieval] ---")
        print(f"Query Passed to retrieve(): \"{ex['text']}\"")
        approach_a_results = retrieve(query=ex["text"], top_k=5)
        print_top_k_results(approach_a_results, "Approach A Top-5 Results")

        # 3. Approach B: NER-Driven Retrieval
        print("\n--- [3. Approach B: NER-Driven Retrieval] ---")
        ner_retrieval_out = retrieve_by_ner(ner_result=ner_out, top_k=5)
        print(f"Generated Queries: {json.dumps(ner_retrieval_out['queries'])}")

        for res_group in ner_retrieval_out["results"]:
            offence = res_group["offence_type"]
            q_str = res_group["query"]
            top_b = res_group["retrieved"]
            print(f"\n--> Offence Group: '{offence}' (Query: '{q_str}')")
            print_top_k_results(top_b, f"Approach B Top-5 Results for '{offence}'")

        # 4. Legal-Relevance Check & Comparison
        print("\n--- [4. Legal-Relevance Evaluation & Comparison] ---")
        expected_sec_dict = ex.get("expected_sections", {})

        for offence_type, exp_info in expected_sec_dict.items():
            exp_sec = exp_info["section"]
            reason = exp_info["reason"]
            print(f"\nOffence Focus: '{offence_type}'")
            print(f"  Target Specific BNS Section : Section {exp_sec}")
            print(f"  Legal Rationale              : {reason}")

            # Check Approach A
            a_hit = False
            a_rank = None
            a_dist = None
            for item in approach_a_results:
                if str(item["section"]) == str(exp_sec):
                    a_hit = True
                    a_rank = item["rank"]
                    a_dist = item["distance"]
                    break

            # Check Approach B for this specific offence group
            b_group = next((g for g in ner_retrieval_out["results"] if g["offence_type"] == offence_type), None)
            b_hit = False
            b_rank = None
            b_dist = None
            if b_group:
                for item in b_group["retrieved"]:
                    if str(item["section"]) == str(exp_sec):
                        b_hit = True
                        b_rank = item["rank"]
                        b_dist = item["distance"]
                        break

            print(f"  Approach A (Full Narrative) : ", end="")
            if a_hit:
                print(f"PASS (Target Sec {exp_sec} found at Rank {a_rank}, Distance: {a_dist:.4f})")
            else:
                top_secs = [str(r['section']) for r in approach_a_results]
                print(f"FAIL (Target Sec {exp_sec} NOT in Top-5. Retrieved Secs: {top_secs})")

            print(f"  Approach B (NER Query '{offence_type}') : ", end="")
            if b_hit:
                print(f"PASS (Target Sec {exp_sec} found at Rank {b_rank}, Distance: {b_dist:.4f})")
            else:
                top_secs_b = [str(r['section']) for r in b_group["retrieved"]] if b_group else []
                print(f"FAIL (Target Sec {exp_sec} NOT in Top-5. Retrieved Secs: {top_secs_b})")

    print("\n" + "=" * 90)
    print("END OF DIAGNOSTIC COMPARISON EXPERIMENT")
    print("=" * 90)


if __name__ == "__main__":
    run_diagnostic_comparison()
