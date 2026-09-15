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
