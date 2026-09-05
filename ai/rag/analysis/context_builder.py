"""context_builder.py — Legal Context Builder for LawAid RAG.

Located at: ai/rag/analysis/context_builder.py
"""

import copy
from typing import Dict, List, Any


def build_legal_context(ner_result: Dict[str, Any], retrieval_result: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble structured incident facts and grouped BNS retrieval results into a legal context object.

    Args:
        ner_result (dict): Output from extract_entities().
        retrieval_result (dict): Output from retrieve_by_ner().

    Returns:
        dict: Deterministic legal context object containing incident facts and grouped BNS retrieval evidence.
    """
    # Protect input dictionaries from mutation
    ner_safe = copy.deepcopy(ner_result) if isinstance(ner_result, dict) else {}
    ret_safe = copy.deepcopy(retrieval_result) if isinstance(retrieval_result, dict) else {}

    incident_info = {
        "raw_text": ner_safe.get("raw_text", ""),
        "victims": ner_safe.get("victims", []),
        "accused": ner_safe.get("accused", []),
        "persons": ner_safe.get("persons", []),
        "locations": ner_safe.get("locations", []),
        "dates": ner_safe.get("dates", []),
        "times": ner_safe.get("times", []),
        "organizations": ner_safe.get("organizations", []),
        "offence_types": ner_safe.get("offence_types", [])
    }

    legal_context_groups = []
    retrieved_groups = ret_safe.get("results", [])

    for group in retrieved_groups:
        offence_type = group.get("offence_type", "")
        query_str = group.get("query", offence_type)
        retrieved_docs = group.get("retrieved", [])

        formatted_docs = []
        for doc in retrieved_docs:
            formatted_docs.append({
                "rank": doc.get("rank"),
                "id": doc.get("id"),
                "section": str(doc.get("section", "")),
                "clause": doc.get("clause", ""),
                "title": doc.get("title", ""),
                "distance": doc.get("distance"),
                "text": doc.get("text", "")
            })

        legal_context_groups.append({
            "offence_type": offence_type,
            "query": query_str,
            "results": formatted_docs
        })

    return {
        "incident": incident_info,
        "legal_context": legal_context_groups
    }
