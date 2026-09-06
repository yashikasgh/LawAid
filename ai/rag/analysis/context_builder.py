"""context_builder.py — Legal Context Builder for LawAid RAG.

Located at: ai/rag/analysis/context_builder.py
"""

import copy
import re
from typing import Dict, List, Any


def _parse_schedule_1(text: str) -> Dict[str, str]:
    """Extract Schedule I Classification fields from document text."""
    if "Schedule I Classification" not in text:
        return {}
    sched_part = text.split("Schedule I Classification", 1)[1].strip()
    keys = ["offence", "punishment", "cognizable", "bailable", "court"]
    result = {}
    lines = [l.strip() for l in sched_part.split("\n") if l.strip()]

    current_key = None
    for line in lines:
        cleaned_key = line.rstrip(":").lower()
        if cleaned_key in keys:
            current_key = cleaned_key
            result[current_key] = ""
        elif current_key:
            if result[current_key]:
                result[current_key] += " " + line
            else:
                result[current_key] = line
    return result


def _extract_clause_parts(text: str, clause_str: str) -> Dict[str, str]:
    """Extract specific target clause text and main section definition from document text."""
    parts = text.split("Schedule I Classification", 1)
    legal_text = parts[0].strip()

    if "Legal Text:" in legal_text:
        legal_body = legal_text.split("Legal Text:", 1)[1].strip()
    else:
        legal_body = legal_text

    if not clause_str or "(" not in clause_str:
        return {
            "target_clause_text": legal_body,
            "section_definition": ""
        }

    match = re.search(r"\(([^)]+)\)", clause_str)
    if not match:
        return {
            "target_clause_text": legal_body,
            "section_definition": ""
        }

    sub_num = match.group(1)

    def_match = re.search(r"(\(1\)\s*.*?(?=\n\s*\(\d+\)|\Z))", legal_body, re.DOTALL)
    section_def = def_match.group(1).strip() if def_match and sub_num != "1" else ""

    pattern = r"(\(" + re.escape(sub_num) + r"\)\s*.*?(?=\n\s*\(\d+\)|\Z))"
    c_match = re.search(pattern, legal_body, re.DOTALL)
    target_clause = c_match.group(1).strip() if c_match else legal_body

    return {
        "target_clause_text": target_clause,
        "section_definition": section_def
    }


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

    if isinstance(retrieval_result, list):
        retrieved_groups = [{"offence_type": "reranked_candidates", "query": "", "retrieved": copy.deepcopy(retrieval_result)}]
    elif isinstance(ret_safe, dict):
        if "results" in ret_safe:
            retrieved_groups = ret_safe["results"]
        elif "candidates" in ret_safe:
            retrieved_groups = [{"offence_type": "reranked_candidates", "query": "", "retrieved": ret_safe["candidates"]}]
        elif "retrieved" in ret_safe:
            retrieved_groups = [{"offence_type": "reranked_candidates", "query": "", "retrieved": ret_safe["retrieved"]}]
        else:
            retrieved_groups = []
    else:
        retrieved_groups = []

    for group in retrieved_groups:
        offence_type = group.get("offence_type", "")
        query_str = group.get("query", offence_type)
        retrieved_docs = group.get("retrieved", [])

        formatted_docs = []
        for doc in retrieved_docs:
            raw_doc_text = doc.get("text", "")
            clause_str = doc.get("clause", "") or ""
            clause_parts = _extract_clause_parts(raw_doc_text, clause_str)
            schedule_1_raw = doc.get("schedule_1") or _parse_schedule_1(raw_doc_text)

            schedule_1 = {
                "offence": schedule_1_raw.get("offence", "") if isinstance(schedule_1_raw, dict) else "",
                "punishment": schedule_1_raw.get("punishment", "") if isinstance(schedule_1_raw, dict) else "",
                "cognizable": schedule_1_raw.get("cognizable", "") if isinstance(schedule_1_raw, dict) else "",
                "bailable": schedule_1_raw.get("bailable", "") if isinstance(schedule_1_raw, dict) else "",
                "court": schedule_1_raw.get("court", "") if isinstance(schedule_1_raw, dict) else ""
            }

            doc_id = doc.get("document_id") or doc.get("id") or ""

            formatted_item = {
                "rank": doc.get("rank"),
                "id": doc_id,
                "document_id": doc_id,
                "section": str(doc.get("section", "")),
                "clause": clause_str,
                "title": doc.get("title", ""),
                "distance": doc.get("distance"),
                "target_clause_text": clause_parts["target_clause_text"],
                "section_definition": clause_parts["section_definition"],
                "schedule_1": schedule_1,
                "text": raw_doc_text
            }

            if "rerank_score" in doc:
                formatted_item["rerank_score"] = doc["rerank_score"]
            if "scoring_reasons" in doc:
                formatted_item["scoring_reasons"] = doc["scoring_reasons"]

            formatted_docs.append(formatted_item)

        legal_context_groups.append({
            "offence_type": offence_type,
            "query": query_str,
            "results": formatted_docs
        })

    return {
        "incident": incident_info,
        "legal_context": legal_context_groups
    }
