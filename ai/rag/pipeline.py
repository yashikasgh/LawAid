"""pipeline.py — LawAid End-to-End Analysis Pipeline.

Located at: ai/rag/pipeline.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root and analysis/retrieval packages are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

RETRIEVAL_DIR = PROJECT_ROOT / "ai" / "rag" / "retrieval"
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

from ai.security.privacy_gateway import sanitize_text
from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import analyze_incident, GroqLLMClient, LLMClient


LEGAL_DISCLAIMER = (
    "Legal analysis provided by LawAid AI is for informational and educational purposes only. "
    "It does not constitute formal legal advice or substitute for consultation with a qualified legal professional."
)


def run_pipeline(
    raw_incident: str,
    llm_client: Optional[LLMClient] = None,
    top_k_retrieval: int = 20,
    top_k_rerank: int = 5
) -> Dict[str, Any]:
    """
    Executes the end-to-end LawAid RAG Legal Analysis Pipeline.

    Flow:
        Raw incident
        → Privacy Gateway (local sanitization before any cloud call)
        → NER (entity extraction on sanitized text)
        → Query Generator (retrieval query formulation)
        → ChromaDB Vector Retrieval (Top-20 per query)
        → Reranker (deterministic reranking to Top-5)
        → Context Builder & Legal Analyzer (grounded analysis via LLM)
        → Final Structured Result

    Args:
        raw_incident (str): Original input incident description text.
        llm_client (LLMClient, optional): Swappable LLM generation backend instance.
            If None, resolves to GroqLLMClient() once at the pipeline boundary.
        top_k_retrieval (int): Number of candidates to retrieve per query from ChromaDB.
        top_k_rerank (int): Number of top reranked candidates to pass to Context Builder/Analyzer.

    Returns:
        dict: Structured analysis result containing:
            - status
            - sanitized_incident
            - privacy_metadata (detections, replacement_map)
            - analysis (grounded legal analysis list)
            - limitations
            - disclaimer (non-binding legal advisory statement)
    """
    # 1. Resolve LLM client ONCE at the pipeline boundary
    if llm_client is None:
        llm_client = GroqLLMClient()

    # 2. Privacy Gateway: Local sanitization boundary
    privacy_res = sanitize_text(raw_incident)
    sanitized_text = privacy_res.get("sanitized_text", "")

    # 3. NER Entity Extraction
    ner_result = extract_entities(sanitized_text)

    # 4. Query Generation
    query_output = generate_queries(ner_result, llm_client=llm_client)
    raw_queries = query_output.get("queries", [])
    queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]

    # Fallback to sanitized raw text if no queries generated
    if not queries and sanitized_text:
        queries = [sanitized_text]

    # 5. ChromaDB Retrieval & Deduplication
    candidate_map: Dict[str, Dict[str, Any]] = {}
    for q_str in queries:
        try:
            retrieved = retrieve(query=q_str, top_k=top_k_retrieval)
            for item in retrieved:
                doc_id = item.get("id")
                if not doc_id:
                    continue
                if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
                    candidate_map[doc_id] = item
        except Exception:
            continue

    raw_candidates = list(candidate_map.values())

    # 6. Reranking (Top-5)
    reranked_top_5 = rerank_candidates(
        incident_input=ner_result,
        candidates=raw_candidates,
        top_k=top_k_rerank
    )

    # 7. Legal Analysis (Internal context building & evidence grounding)
    analysis_result = analyze_incident(
        ner_result=ner_result,
        retrieval_result=reranked_top_5,
        llm_client=llm_client
    )

    # 8. Return Final Pipeline Structure
    return {
        "status": analysis_result.get("status", "success"),
        "sanitized_incident": sanitized_text,
        "privacy_metadata": {
            "detections": privacy_res.get("detections", []),
            "replacement_map": privacy_res.get("replacement_map", {})
        },
        "analysis": analysis_result.get("analysis", []),
        "limitations": analysis_result.get("limitations", []),
        "disclaimer": LEGAL_DISCLAIMER
    }
