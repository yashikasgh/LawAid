import sys
import time
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
# Attempt to import the real BNS RAG retrieval pipeline and end-to-end analyzer.
# run_pipeline: Sanitization -> NER -> Groq Queries -> ChromaDB -> Rerank -> Groq Legal Reasoning
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # LawAid/
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from ai.rag.pipeline import run_pipeline as _run_pipeline  # type: ignore
    _PIPELINE_AVAILABLE = True
except Exception:
    _PIPELINE_AVAILABLE = False

try:
    from ai.rag.retrieval.retrieve_bns import retrieve as _retrieve_bns  # type: ignore
    _RAG_AVAILABLE = True
except Exception:
    _RAG_AVAILABLE = False

# ---------------------------------------------------------------------------

router = APIRouter(prefix="/fir", tags=["fir"])


# ── Full Legal Incident Analysis (End-to-End AI Pipeline) ────────────────────

class IncidentAnalysisRequest(BaseModel):
    incident: str


@router.post("/analyze")
def analyze_incident_endpoint(body: IncidentAnalysisRequest):
    """
    Executes the end-to-end LawAid AI Legal Analysis Pipeline on raw incident text.
    Handles Privacy Sanitization -> NER -> Query Generation -> Retrieval ->
    Reranking -> LLM Grounded Analysis (Groq GPT-OSS 120B).

    Returns structured analysis with offences, applicability, reasoning,
    punishment, bailable/cognizable classifications, and privacy metadata.
    """
    raw_incident = body.incident.strip()
    if len(raw_incident) < 5:
        raise HTTPException(status_code=400, detail="Incident description is too short.")

    if _PIPELINE_AVAILABLE:
        try:
            res = _run_pipeline(raw_incident=raw_incident)
            return {"status": "ok", "source": "pipeline", "data": res}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI Pipeline Error: {str(e)}")
    
    raise HTTPException(status_code=500, detail="AI Pipeline module not found or unavailable.")


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
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"BNS Retrieval Error: {str(e)}")

    raise HTTPException(status_code=500, detail="BNS Retrieval module not found or unavailable.")


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


# ── FIR Understand (P1 Task 6) ───────────────────────────────────────────────

@router.post("/understand")
async def understand_fir(file: UploadFile = File(...)):
    """
    Accepts an uploaded FIR (PDF or image).
    Extracts text using PyMuPDF, processes charges and legal analysis,
    and returns an empathetic, plain-language summary, citizen rights, and next steps.
    """
    if file.content_type not in ["application/pdf", "image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only PDF, JPEG, PNG files allowed")

    contents = await file.read()
    try:
        file_id = str(fs.put(contents, filename=file.filename, content_type=file.content_type))
    except Exception:
        file_id = "doc_" + str(int(time.time()))

    extracted_text = ""
    # 1. PDF Text Extraction
    if file.content_type == "application/pdf":
        try:
            import pymupdf
            doc = pymupdf.open(stream=contents, filetype="pdf")
            extracted_text = "\n".join([page.get_text() for page in doc]).strip()
        except Exception:
            extracted_text = ""

    # 2. Extract charges and summarize
    charges_summary = []
    plain_summary = ""
    if extracted_text and len(extracted_text) >= 15:
        if _PIPELINE_AVAILABLE:
            try:
                ai_res = _run_pipeline(raw_incident=extracted_text[:2500])
                for item in ai_res.get("analysis", []):
                    charges_summary.append({
                        "section": item.get("section", ""),
                        "title": item.get("title", ""),
                        "punishment": item.get("punishment", ""),
                        "bailable": item.get("bailable", ""),
                        "reasoning": item.get("reasoning", ""),
                    })
                plain_summary = (
                    f"Official police complaint document recorded. The allegations involve "
                    f"{', '.join([c['title'] for c in charges_summary if c.get('title')]) or 'cognizable offences'}.\n\n"
                    f"Key facts stated in FIR:\n"
                    + (extracted_text[:400] + ("..." if len(extracted_text) > 400 else ""))
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"AI Pipeline Error: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail="AI Pipeline module not found or unavailable.")

    if not plain_summary:
        raise HTTPException(status_code=400, detail="Could not extract text from the document.")

    rights = [
        "Right to a free copy of the First Information Report (FIR) immediately under Section 173 BNSS.",
        "Right to know the full grounds of arrest and whether offences are bailable or non-bailable.",
        "Right to consult and be defended by a legal practitioner of your choice (Article 22(1) of the Constitution).",
        "Right to free legal assistance if unable to afford counsel (NALSA / Legal Services Authority).",
        "Protection against unlawful detention beyond 24 hours without production before a Magistrate (Section 58 BNSS).",
    ]

    next_steps = [
        "Carefully verify all allegations, dates, times, and witness names mentioned in the FIR.",
        "If offences are marked Non-Bailable, consult an advocate immediately to file for Anticipatory Bail under Section 482 BNSS.",
        "Contact the District Legal Services Authority (DLSA) or call Helpline 15100 for free assistance.",
        "Keep multiple physical copies and preserve timestamped digital evidence (calls, receipts, CCTV footage).",
    ]

    return {
        "status": "ok",
        "file_id": file_id,
        "filename": file.filename,
        "extracted_text": extracted_text[:1200] if extracted_text else "(Document received as scanned image/attachment)",
        "summary": plain_summary,
        "charges": charges_summary,
        "rights": rights,
        "next_steps": next_steps,
    }


# ── FIR Get / Generate (P1 Task 7) ───────────────────────────────────────────

class FIRGenerateRequest(BaseModel):
    complaint: str
    station_code: str = "PS001"
    district: str = "Central"
    complainant_name: str = "Protected / Citizen"


@router.post("/generate")
def generate_fir(body: FIRGenerateRequest = None):
    """
    Generates a formal First Information Report (FIR) draft as a PDF.
    Returns official FIR ID, generated timestamp, and verification hash.
    """
    import hashlib
    import datetime
    import io
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation module (reportlab) not installed.")

    now = datetime.datetime.now()
    year = now.year
    seq = int(now.timestamp()) % 10000
    fir_id = f"FIR/{year}/{seq:04d}"

    complaint_text = body.complaint if body and body.complaint else "General complaint lodged."
    complainant_name = body.complainant_name if body and body.complainant_name else "Citizen"
    station_code = body.station_code if body else "PS001"

    # Create PDF in memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "FIRST INFORMATION REPORT (FIR)")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"FIR ID: {fir_id}")
    c.drawString(50, height - 100, f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(50, height - 120, f"Police Station: {station_code}")
    c.drawString(50, height - 140, f"Complainant: {complainant_name}")
    
    c.drawString(50, height - 170, "Incident Description:")
    c.setFont("Helvetica", 10)
    
    # Wrap text
    import textwrap
    lines = textwrap.wrap(complaint_text, width=80)
    y_pos = height - 190
    for line in lines:
        c.drawString(50, y_pos, line)
        y_pos -= 15
        if y_pos < 100:
            c.showPage()
            c.setFont("Helvetica", 10)
            y_pos = height - 50
    
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    # Store in MongoDB
    from app.core.mongo import fs
    file_id = fs.put(pdf_bytes, filename=f"{fir_id.replace('/', '_')}.pdf", content_type="application/pdf", metadata={"fir_id": fir_id, "hash": sha256_hash})

    return {
        "fir_id": fir_id,
        "status": "draft_created",
        "sha256_hash": sha256_hash,
        "created_at": now.isoformat(),
        "station_code": station_code,
        "district": body.district if body else "Central",
        "pdf_url": f"/api/fir/download/{str(file_id)}",
        "summary": f"Draft FIR registered under ID {fir_id}. Ready for official review and station stamp.",
    }

from fastapi.responses import StreamingResponse

@router.get("/download/{file_id}")
def download_fir(file_id: str):
    from bson.objectid import ObjectId
    try:
        file_data = fs.get(ObjectId(file_id))
        return StreamingResponse(
            file_data,
            media_type=file_data.content_type,
            headers={"Content-Disposition": f"attachment; filename={file_data.filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")

@router.get("/{fir_id}")
def get_fir(fir_id: str):
    return {
        "fir_id": fir_id,
        "status": "registered",
        "message": f"FIR record {fir_id} on file.",
    }


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