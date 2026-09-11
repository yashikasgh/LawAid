"""debug_mock_llm.py — Verify RAG pipeline when LLM generation succeeds.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.security.privacy_gateway import sanitize_text
from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import analyze_incident, MockLLMClient
from ai.rag.pipeline import run_chat_pipeline, run_pipeline

DEMO_INCIDENT = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

def test_mock_llm():
    print("=" * 80)
    print("TESTING RAG PIPELINE WITH MOCK LLM (SIMULATING ONLINE LLM)")
    print("=" * 80)

    # Mock response for query generator (if called)
    mock_query_json = json.dumps({
        "queries": [
            {"query_type": "incident_context", "query": "stole mobile phone after punching"},
            {"query_type": "fact_focused", "query": "unknown man punched victim stole mobile phone"},
            {"query_type": "legal_concept", "query": "dishonest taking of movable property without consent"}
        ]
    })

    # Mock response for legal analyzer
    mock_analysis_json = json.dumps({
        "status": "success",
        "analysis": [
            {
                "document_id": "bns_303_303(2)-2",
                "applicability": "supported",
                "reasoning": "The accused dishonestly took the victim's mobile phone without consent, satisfying all essential elements of theft under BNS Section 303."
            },
            {
                "document_id": "bns_134",
                "applicability": "supported",
                "reasoning": "The accused punched the victim (used assault/force) in attempting to commit theft of property carried by the victim."
            },
            {
                "document_id": "bns_309_309(4)-2",
                "applicability": "uncertain",
                "reasoning": "Robbery requires hurt caused in order to commit theft; further facts are required to establish whether punching was directly in order to commit theft vs a separate assault."
            }
        ],
        "limitations": []
    })

    # Mock response for conversational chat synthesis
    mock_chat_json = json.dumps({
        "reply": "Based on your description, the incident involves dishonest taking of your mobile phone without consent (BNS Section 303: Theft) accompanied by physical assault (BNS Section 134: Assault in attempting theft). You can ask the police to register an FIR under Section 303 and Section 134 of the Bharatiya Nyaya Sanhita, 2023."
    })

    mock_client = MockLLMClient(responses=[mock_query_json, mock_analysis_json, mock_chat_json])

    # Run pipeline
    pipeline_res = run_pipeline(DEMO_INCIDENT, llm_client=mock_client)
    print("\n--- RUN_PIPELINE OUTPUT ---")
    print(f"Status: {pipeline_res.get('status')}")
    print("Analysis items count:", len(pipeline_res.get("analysis", [])))
    print(json.dumps(pipeline_res.get("analysis"), indent=2))

    # Run chat pipeline
    mock_client_chat = MockLLMClient(responses=[mock_query_json, mock_analysis_json, mock_chat_json])
    chat_res = run_chat_pipeline(DEMO_INCIDENT, llm_client=mock_client_chat)
    print("\n--- RUN_CHAT_PIPELINE OUTPUT ---")
    print(f"Status: {chat_res.get('status')}")
    print(f"Sections recommended: {chat_res.get('sections')}")
    print(f"Reply:\n{chat_res.get('reply')}")

if __name__ == "__main__":
    test_mock_llm()
