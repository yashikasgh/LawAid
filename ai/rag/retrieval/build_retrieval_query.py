"""build_retrieval_query.py — NER -> Baseline Retrieval Integration Layer.

Located at: ai/rag/retrieval/build_retrieval_query.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Ensure retrieval directory is on sys.path to import retrieve_bns cleanly
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from retrieve_bns import retrieve, TOP_K


def build_retrieval_queries(ner_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert structured NER result offence_types into targeted vector retrieval queries.

    Args:
        ner_result (dict): Dictionary output from extract_entities().

    Returns:
        dict: Structured query information containing a list of query objects.
    """
    if not isinstance(ner_result, dict):
        return {"queries": []}

    offence_types = ner_result.get("offence_types", [])
    if not offence_types:
        return {"queries": []}

    raw_text = str(ner_result.get("raw_text", "")).strip()

    queries = []
    for offence in offence_types:
        offence_str = str(offence).strip()
        if offence_str:
            query_str = f"{offence_str} {raw_text}".strip() if raw_text else offence_str
            queries.append({
                "offence_type": offence_str,
                "query": query_str
            })

    return {"queries": queries}


def retrieve_by_ner(ner_result: Dict[str, Any], top_k: int = TOP_K) -> Dict[str, Any]:
    """Execute vector retrieval for each controlled offence query in ner_result.

    Args:
        ner_result (dict): Dictionary output from extract_entities().
        top_k (int): Number of top results to retrieve per offence.

    Returns:
        dict: Grouped retrieval results by offence type.
    """
    query_info = build_retrieval_queries(ner_result)
    queries = query_info.get("queries", [])

    if not queries:
        return {
            "queries": [],
            "results": []
        }

    results = []
    for q_item in queries:
        offence_type = q_item["offence_type"]
        query_str = q_item["query"]

        retrieved_list = retrieve(query=query_str, top_k=top_k)
        results.append({
            "offence_type": offence_type,
            "query": query_str,
            "retrieved": retrieved_list
        })

    return {
        "queries": queries,
        "results": results
    }
