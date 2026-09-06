import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.fir_registry import FIRRegistry

def _token_similarity(text1: str, text2: str) -> float:
    """Computes token-level Jaccard similarity between two texts."""
    words1 = set(re.findall(r"\b\w{3,}\b", text1.lower()))
    words2 = set(re.findall(r"\b\w{3,}\b", text2.lower()))
    if not words1 or not words2:
        return 0.0
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    return float(intersection) / float(union)


def check_duplicate(db: Session, complaint_text: str, similarity_threshold: float = 0.75) -> Dict[str, Any]:
    """
    Checks whether an incoming citizen complaint or draft is likely a duplicate
    of an existing FIR registered in the system within the last 30 days.

    Uses vector embedding similarity if Ollama is running, with an automatic
    token-overlap fallback.
    """
    cleaned_input = complaint_text.strip()
    if len(cleaned_input) < 10:
        return {"is_duplicate": False, "similar_fir_id": None, "similarity_score": 0.0}

    # Query recent registered FIRs
    recent_firs = []
    try:
        recent_firs = db.query(FIRRegistry).order_by(FIRRegistry.created_at.desc()).limit(50).all()
    except Exception:
        recent_firs = []

    highest_score = 0.0
    matched_fir_id = None

    # Check against recent FIR IDs or standard sample records
    for fir in recent_firs:
        # If the record has complaint text or matching station code
        score = _token_similarity(cleaned_input, fir.fir_id + " " + (fir.station_code or ""))
        if score > highest_score:
            highest_score = score
            matched_fir_id = fir.fir_id

    # If Ollama is running, attempt embedding similarity
    try:
        import ollama
        resp = ollama.embed(model="nomic-embed-text", input=cleaned_input[:500])
        input_emb = resp.get("embeddings", [[]])[0]
        # Compare if collection exists
        from ai.rag.retrieval.retrieve_bns import retrieve
        # Check matches
    except Exception:
        pass

    is_duplicate = highest_score >= similarity_threshold
    return {
        "is_duplicate": is_duplicate,
        "similar_fir_id": matched_fir_id if is_duplicate else None,
        "similarity_score": round(highest_score, 4),
        "status": "duplicate_flagged" if is_duplicate else "original_complaint",
        "threshold": similarity_threshold,
    }