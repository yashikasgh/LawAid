from sqlalchemy.orm import Session

def check_duplicate(db: Session, complaint_text: str, similarity_threshold: float = 0.92) -> dict:
    """
    Stub implementation. Real version will:
    1. Embed complaint_text using Person 2's sentence-transformer function
    2. Compare against embeddings of complaints from the last 30 days
    3. Return is_duplicate=True if cosine similarity > threshold
    """
    # TODO: replace with real embedding + cosine similarity once Person 2's
    # embedding function is available
    return {
        "is_duplicate": False,
        "similar_fir_id": None,
        "similarity_score": 0.0,
    }