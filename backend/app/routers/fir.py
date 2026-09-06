import sys
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.mongo import fs
from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.fir_auth import register_fir, verify_fir
from app.models.user import User
from app.services.duplicate_check import check_duplicate

# ---------------------------------------------------------------------------
# Attempt to import the real BNS RAG retrieval pipeline.
# This requires:  Ollama running + nomic-embed-text pulled + ChromaDB index built.
# If any of those are missing the import will fail gracefully and the endpoint
# falls back to the hard-coded mock so the rest of the app keeps working.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # LawAid/
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from ai.rag.retrieval.retrieve_bns import retrieve as _retrieve_bns  # type: ignore
    _RAG_AVAILABLE = True
except Exception:
    _RAG_AVAILABLE = False

# ---------------------------------------------------------------------------

router = APIRouter(prefix="/fir", tags=["fir"])


# ── BNS Search ──────────────────────────────────────────────────────────────

@router.get("/bns/search")
def search_bns(query: str = Query(..., min_length=3)):
    """
    Returns BNS sections relevant to the citizen's complaint text.

    Tries real RAG retrieval first (ChromaDB + Ollama).
    Falls back to two hard-coded example results if the AI stack is not yet
    set up locally (Ollama not installed / ChromaDB index not built).

    Response shape (see shared/schemas/api_contracts.md):
        { status, source, results: [{ rank, section, clause, title, text,
                                      chapter, bailable, cognizable, similarity }] }
    """
    if _RAG_AVAILABLE:
        try:
            raw = _retrieve_bns(query=query, top_k=5)
            results = []
            for item in raw:
                # ChromaDB cosine distance: 0 = identical, 1 = orthogonal.
                # Convert to a 0–1 similarity score citizens can understand.
                distance = float(item.get("distance", 1.0))
                similarity = round(max(0.0, 1.0 - distance), 4)
                meta = item  # retrieve() merges metadata into the item dict
                results.append({
                    "rank": item.get("rank", 0),
                    "section": str(item.get("section", "")),
                    "clause": item.get("clause", ""),
                    "title": item.get("title", ""),
                    "text": item.get("text", ""),
                    "chapter": item.get("chapter", ""),
                    "bailable": item.get("bailable", ""),
                    "cognizable": item.get("cognizable", ""),
                    "similarity": similarity,
                })
            # Filter out low-confidence matches
            results = [r for r in results if r["similarity"] >= 0.30]
            if not results:
                return {"status": "insufficient_information", "source": "rag", "results": []}
            return {"status": "ok", "source": "rag", "results": results}
        except Exception:
            # Fall through to mock on any runtime error (e.g., Ollama not running)
            pass

    # ── Mock fallback (remove once Ollama + ChromaDB are set up) ────────────
    mock_results = [
        {
            "rank": 1,
            "section": "318",
            "clause": "",
            "title": "Cheating",
            "text": (
                "Whoever, by deceiving any person, fraudulently or dishonestly induces "
                "the person so deceived to deliver any property to any person, or to consent "
                "that any person shall retain any property, or intentionally induces the person "
                "so deceived to do or omit to do anything which he would not do or omit if he "
                "were not so deceived, and which act or omission causes or is likely to cause "
                "damage or harm to that person in body, mind, reputation or property, is said "
                "to 'cheat'."
            ),
            "chapter": "CHAPTER XVII",
            "bailable": "Bailable",
            "cognizable": "Non-Cognizable",
            "similarity": 0.81,
        },
        {
            "rank": 2,
            "section": "351",
            "clause": "",
            "title": "Criminal Intimidation",
            "text": (
                "Whoever threatens another with any injury to his person, reputation or "
                "property, or to the person or reputation of any one in whom that person is "
                "interested, with intent to cause alarm to that person, or to cause that person "
                "to do any act which he is not legally bound to do, or to omit to do any act "
                "which that person is legally entitled to do, as the means of avoiding the "
                "execution of such threat, commits criminal intimidation."
            ),
            "chapter": "CHAPTER XVII",
            "bailable": "Bailable",
            "cognizable": "Non-Cognizable",
            "similarity": 0.68,
        },
    ]
    top = mock_results[0]
    if top["similarity"] < 0.72:
        return {"status": "insufficient_information", "source": "mock", "results": []}
    return {"status": "ok", "source": "mock", "results": mock_results}


# ── FIR Upload ───────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_fir(file: UploadFile = File(...)):
    if file.content_type not in ["application/pdf", "image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only PDF, JPEG, PNG files allowed")

    contents = await file.read()
    file_id = fs.put(contents, filename=file.filename, content_type=file.content_type)

    return {
        "status": "uploaded",
        "file_id": str(file_id),
        "filename": file.filename,
    }


# ── FIR Register ─────────────────────────────────────────────────────────────

@router.post("/register")
async def register_fir_route(
    file: UploadFile = File(...),
    station_code: str = "PS001",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contents = await file.read()
    record = register_fir(
        db=db,
        file_bytes=contents,
        officer_id=current_user.id,
        station_code=station_code,
    )
    return {
        "fir_id": record.fir_id,
        "sha256_hash": record.sha256_hash,
        "status": record.status,
        "created_at": record.created_at,
    }


# ── FIR Verify ───────────────────────────────────────────────────────────────

@router.post("/verify")
async def verify_fir_route(
    fir_id: str = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    result = verify_fir(db=db, fir_id=fir_id, file_bytes=contents)
    return result


# ── FIR Get / Generate (stubs) ───────────────────────────────────────────────

@router.get("/{fir_id}")
def get_fir(fir_id: str):
    return {"fir_id": fir_id, "status": "not_implemented"}


@router.post("/generate")
def generate_fir():
    return {"fir_id": "STUB-001", "status": "not_implemented"}


# ── Duplicate Check ──────────────────────────────────────────────────────────

class DuplicateCheckRequest(BaseModel):
    complaint_text: str


@router.post("/check-duplicate")
def check_duplicate_route(body: DuplicateCheckRequest, db: Session = Depends(get_db)):
    """
    Checks whether a complaint is likely a duplicate of an existing FIR.
    Accepts a JSON body { complaint_text } (not a query parameter).
    Currently a stub — returns is_duplicate=False always.
    """
    result = check_duplicate(db, body.complaint_text)
    return result