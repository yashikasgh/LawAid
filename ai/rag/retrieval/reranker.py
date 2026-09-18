"""reranker.py — Semantic candidate reranker using Reciprocal Rank Fusion (RRF) for LawAid RAG.

Located at: ai/rag/retrieval/reranker.py
"""

from typing import List, Dict, Any, Union, Optional


def rerank_candidates(
    incident_input: Union[str, Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    top_k: Optional[int] = None,
    rrf_k: int = 60
) -> List[Dict[str, Any]]:
    """
    Reranks legal candidate documents using pure vector similarity and Reciprocal Rank Fusion (RRF).
    Contains ZERO hardcoded legal rules, section number mappings, or keyword heuristics.

    Args:
        incident_input: Raw incident text or NER dictionary (unused for rule matching).
        candidates: List of candidate dictionaries retrieved from ChromaDB.
        top_k: Optional number of top candidates to return.
        rrf_k: RRF constant parameter (default 60).

    Returns:
        Sorted list of candidate dictionaries containing semantic rerank metadata:
        - document_id (or id)
        - original distance
        - rerank_score (RRF score + normalized vector similarity)
        - scoring_reasons
    """
    if not candidates:
        return []

    # Map doc_id -> merged candidate record
    candidate_map: Dict[str, Dict[str, Any]] = {}

    for idx, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            continue

        doc_id = str(cand.get("id") or cand.get("document_id") or "")
        if not doc_id:
            continue

        orig_rank = int(cand.get("rank", idx + 1))
        orig_distance = float(cand.get("distance", 1.0))

        # Base vector similarity (0.0 to 1.0 scale approx from cosine distance)
        similarity = max(0.0, 1.0 - (orig_distance / 2.0))

        # RRF contribution for this occurrence
        rrf_term = 1.0 / (rrf_k + orig_rank)

        if doc_id not in candidate_map:
            cand_copy = dict(cand)
            cand_copy["document_id"] = doc_id
            cand_copy["id"] = doc_id
            cand_copy["best_distance"] = orig_distance
            cand_copy["best_similarity"] = similarity
            cand_copy["rrf_score"] = rrf_term
            cand_copy["occurrences"] = 1
            candidate_map[doc_id] = cand_copy
        else:
            existing = candidate_map[doc_id]
            existing["rrf_score"] += rrf_term
            existing["occurrences"] += 1
            if orig_distance < existing["best_distance"]:
                existing["best_distance"] = orig_distance
                existing["best_similarity"] = similarity

    reranked = []
    for doc_id, cand_data in candidate_map.items():
        # Final rerank score combines RRF score and best vector similarity
        final_score = round(cand_data["rrf_score"] + (cand_data["best_similarity"] * 0.1), 6)

        reasons = [
            f"Semantic vector similarity score: {cand_data['best_similarity']:.4f} (best distance: {cand_data['best_distance']:.4f})",
            f"Reciprocal Rank Fusion (RRF) score: {cand_data['rrf_score']:.6f} across {cand_data['occurrences']} retrieval query occurrence(s)"
        ]

        cand_data["rerank_score"] = final_score
        cand_data["distance"] = cand_data["best_distance"]
        cand_data["scoring_reasons"] = reasons

        # Clean up temporary fields
        del cand_data["best_distance"]
        del cand_data["best_similarity"]
        del cand_data["rrf_score"]
        del cand_data["occurrences"]

        reranked.append(cand_data)

    # Sort candidates by rerank_score in descending order
    reranked.sort(key=lambda x: x.get("rerank_score", -999.0), reverse=True)

    if top_k is not None and isinstance(top_k, int) and top_k > 0:
        return reranked[:top_k]

    return reranked


def rerank_section_candidates(
    candidates: List[Dict[str, Any]],
    top_k: Optional[int] = None,
    rrf_k: int = 60
) -> List[Dict[str, Any]]:
    """Reranks legal candidates at the Parent Legal Section level using Reciprocal Rank Fusion (RRF).

    Unique Query Cumulative RRF Formulation:
    - Group raw candidate clause documents by parent section number and query occurrence.
    - For each unique query q retrieving section S, take the best-ranked clause rank r_best(S, q).
    - Contribute 1 / (rrf_k + r_best(S, q)) to the section's cumulative RRF score.
    - Add 0.1 * best_similarity(S).
    - Retains all child clause document dicts attached under each parent section record.

    Args:
        candidates (list): Flat list of raw candidate document dicts retrieved across queries from ChromaDB.
        top_k (int, optional): Optional number of top section candidates to return (None for full pool).
        rrf_k (int): RRF constant parameter (default 60).

    Returns:
        list: Sorted list of parent section candidate records containing:
        - section: str section number
        - title: str section title
        - section_rrf_score: float combined section RRF score
        - clauses: list of all child clause document dicts belonging to section
        - scoring_reasons: list of explanatory strings
    """
    if not candidates:
        return []

    section_map: Dict[str, Dict[str, Any]] = {}

    for idx, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            continue

        sec = str(cand.get("section", "")).strip()
        doc_id = str(cand.get("id") or cand.get("document_id") or "")
        if not sec or not doc_id:
            continue

        orig_rank = int(cand.get("rank", idx + 1))
        orig_distance = float(cand.get("distance", 1.0))
        query_key = str(cand.get("query") or cand.get("query_str") or (idx // 20))
        similarity = max(0.0, 1.0 - (orig_distance / 2.0))

        if sec not in section_map:
            section_map[sec] = {
                "section": sec,
                "title": cand.get("title", ""),
                "best_distance": orig_distance,
                "best_similarity": similarity,
                "query_best_ranks": {query_key: orig_rank},
                "clauses": [dict(cand)],
                "seen_doc_ids": {doc_id}
            }
        else:
            sec_entry = section_map[sec]
            if doc_id not in sec_entry["seen_doc_ids"]:
                sec_entry["clauses"].append(dict(cand))
                sec_entry["seen_doc_ids"].add(doc_id)
            if orig_distance < sec_entry["best_distance"]:
                sec_entry["best_distance"] = orig_distance
                sec_entry["best_similarity"] = similarity
                if cand.get("title") and not sec_entry["title"]:
                    sec_entry["title"] = cand.get("title")

            if query_key not in sec_entry["query_best_ranks"] or orig_rank < sec_entry["query_best_ranks"][query_key]:
                sec_entry["query_best_ranks"][query_key] = orig_rank

    section_reranked = []
    for sec, sec_entry in section_map.items():
        # Formula D: Diminishing Multi-Query Section-Level RRF formulation.
        # Applies diminishing weights (1.0, 0.5, 0.25, 0.125) to top-4 unique query contributions (sorted descending)
        # to preserve multi-query consensus without allowing generic multi-query sections to swamp single-query matches.
        raw_rrf_terms = sorted([1.0 / (rrf_k + rk) for rk in sec_entry["query_best_ranks"].values()], reverse=True)
        diminishing_weights = (1.0, 0.5, 0.25, 0.125)
        rrf_sum = sum(term * w for term, w in zip(raw_rrf_terms[:4], diminishing_weights))

        best_sim = sec_entry["best_similarity"]
        final_section_score = round(rrf_sum + (best_sim * 0.1), 6)

        query_count = len(sec_entry["query_best_ranks"])
        reasons = [
            f"Parent section best vector similarity: {best_sim:.4f} (best distance: {sec_entry['best_distance']:.4f})",
            f"Section-level Unique Query RRF score: {rrf_sum:.6f} across {query_count} unique query formulation(s)",
            f"Child clause documents preserved: {len(sec_entry['clauses'])}"
        ]

        sec_record = {
            "section": sec,
            "title": sec_entry["title"],
            "section_rrf_score": final_section_score,
            "rerank_score": final_section_score,
            "best_distance": sec_entry["best_distance"],
            "best_similarity": best_sim,
            "query_occurrences": query_count,
            "clauses": sec_entry["clauses"],
            "scoring_reasons": reasons
        }
        section_reranked.append(sec_record)

    section_reranked.sort(key=lambda x: x.get("section_rrf_score", -999.0), reverse=True)

    if top_k is not None and isinstance(top_k, int) and top_k > 0:
        return section_reranked[:top_k]

    return section_reranked

