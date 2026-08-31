"""test_analysis_pipeline.py — Diagnostic Integration Test for Phase 3B Pipeline.

Located at: ai/rag/analysis/test_analysis_pipeline.py
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add module directories to sys.path
NER_DIR = PROJECT_ROOT / "ai" / "rag" / "ner"
RETRIEVAL_DIR = PROJECT_ROOT / "ai" / "rag" / "retrieval"
ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"

for d in [NER_DIR, RETRIEVAL_DIR, ANALYSIS_DIR]:
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from ner_extractor import extract_entities
from build_retrieval_query import retrieve_by_ner
from context_builder import build_legal_context
from legal_analyzer import analyze_incident, MockLLMClient, OllamaLLMClient


EXAMPLE_2_INCIDENT = (
    "Sub-Inspector Sharma recorded that the accused Sunil illegally entered the shop in Chandni Chowk "
    "and threatened to kill the shopkeeper Vijay if he called the police."
)


def run_pipeline_diagnostic():
    print("=" * 90)
    print("PHASE 3B DIAGNOSTIC INTEGRATION TEST: END-TO-END RAG ANALYSIS PIPELINE")
    print("=" * 90)
    print(f"Input Incident Narrative:\n\"{EXAMPLE_2_INCIDENT}\"\n")

    # Step 1: NER Entity Extraction
    print("--- [Step 1: NER Output] ---")
    ner_out = extract_entities(EXAMPLE_2_INCIDENT)
    print(json.dumps(ner_out, indent=2))

    # Step 2: NER-Driven Retrieval
    print("\n--- [Step 2: NER-Driven Retrieval Queries & Top-K Results] ---")
    retrieval_out = retrieve_by_ner(ner_out, top_k=5)
    print("Queries Generated:", json.dumps(retrieval_out["queries"], indent=2))
    
    for res_group in retrieval_out["results"]:
        offence = res_group["offence_type"]
        retrieved_docs = res_group["retrieved"]
        print(f"\nGroup '{offence}': Retrieved {len(retrieved_docs)} docs")
        for doc in retrieved_docs:
            print(f"  Rank {doc['rank']} | ID: {doc['id']:<18} | Sec: {str(doc['section']):<5} | Dist: {doc['distance']:.4f} | {doc['title']}")

    # Step 3: Legal Context Assembly
    print("\n--- [Step 3: Legal Context Object] ---")
    context_obj = build_legal_context(ner_out, retrieval_out)
    print(json.dumps(context_obj, indent=2))

    # Step 4: Generation Backend Status & Structured Legal Analysis
    print("\n--- [Step 4: Generation Backend Status] ---")
    model_name = os.environ.get("OLLAMA_LLM_MODEL")
    if model_name:
        print(f"Configured Generative LLM Model: '{model_name}'")
        llm_client = OllamaLLMClient(model_name=model_name)
    else:
        print("Configured Generative LLM Model: NONE (OLLAMA_LLM_MODEL env var not set).")
        print("Local Ollama has 'nomic-embed-text' (Embedding Model Only).")
        print("Using MockLLMClient to demonstrate structured legal analysis and evidence grounding...\n")

        # Mock structured LLM response grounded strictly in the actual retrieved doc IDs (bns_329_329(1), bns_351_351(2))
        mock_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "offence_type": "criminal trespass",
                    "section": "329",
                    "title": "Criminal trespass and house-trespass.",
                    "applicability": "supported",
                    "reasoning": "The accused Sunil illegally entered the shop premises in Chandni Chowk without authorization.",
                    "punishment": "not_available_in_retrieved_context",
                    "bailable": "not_available_in_retrieved_context",
                    "cognizable": "not_available_in_retrieved_context",
                    "evidence": [
                        {
                            "document_id": "bns_329_329(3)",
                            "section": "329",
                            "clause": "329(3)",
                            "rank": 1
                        }
                    ]
                },
                {
                    "offence_type": "criminal intimidation",
                    "section": "351",
                    "title": "Criminal intimidation.",
                    "applicability": "supported",
                    "reasoning": "The accused Sunil threatened to kill the shopkeeper Vijay if he called the police.",
                    "punishment": "not_available_in_retrieved_context",
                    "bailable": "not_available_in_retrieved_context",
                    "cognizable": "not_available_in_retrieved_context",
                    "evidence": [
                        {
                            "document_id": "bns_351_351(2)",
                            "section": "351",
                            "clause": "351(2)",
                            "rank": 1
                        }
                    ]
                }
            ],
            "limitations": []
        })
        llm_client = MockLLMClient(responses=[mock_response])

    # Step 5: Structured Legal Analysis Execution & Verification
    print("--- [Step 5: Structured Legal Analysis Output] ---")
    analysis_out = analyze_incident(ner_out, retrieval_out, llm_client=llm_client)
    print(json.dumps(analysis_out, indent=2))

    # Step 6: Evidence Verification Report
    print("\n--- [Step 6: Evidence Verification Report] ---")
    for idx, item in enumerate(analysis_out.get("analysis", []), 1):
        sec = item.get("section")
        offence = item.get("offence_type")
        ev_list = item.get("evidence", [])
        print(f"Proposed Item {idx}: Section {sec} ({offence})")
        for ev in ev_list:
            print(f"  -> Evidence Document ID: {ev.get('document_id')} | Clause: {ev.get('clause')} | Rank: {ev.get('rank')}")
    
    if analysis_out.get("limitations"):
        print("\nLimitations / Warnings Recorded:")
        for lim in analysis_out["limitations"]:
            print(f"  - {lim}")

    print("\n" + "=" * 90)
    print("END OF PHASE 3B DIAGNOSTIC INTEGRATION TEST")
    print("=" * 90)


if __name__ == "__main__":
    run_pipeline_diagnostic()
