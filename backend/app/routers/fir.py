import sys
import time
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.mongo import mongo_available

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
    _run_pipeline = None
    _PIPELINE_AVAILABLE = False

try:
    from ai.rag.retrieval.retrieve_bns import retrieve as _retrieve_bns  # type: ignore
    _RAG_AVAILABLE = True
except Exception:
    _retrieve_bns = None
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

    from app.core.mongo import mongo_available, fs as _fs
    if not mongo_available or _fs is None:
        raise HTTPException(
            status_code=503,
            detail="File storage (MongoDB/GridFS) is currently unavailable. Start MongoDB to enable document uploads."
        )

    contents = await file.read()
    try:
        file_id = _fs.put(contents, filename=file.filename, content_type=file.content_type)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"File storage failed: {str(e)}")

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
    """
    Register a FIR. Extracts text from the uploaded file and stores it as complaint_text
    so duplicate detection can compare against it.
    """
    contents = await file.read()

    # Extract complaint text from the uploaded document (for duplicate detection)
    extracted_text = ""
    try:
        extracted_text = _extract_text_with_ocr(contents, file.filename or "", file.content_type or "")
    except Exception:
        extracted_text = ""

    record = register_fir(
        db=db,
        file_bytes=contents,
        officer_id=current_user.id,
        station_code=station_code,
        complaint_text=extracted_text[:2000] if extracted_text else None,  # Store up to 2000 chars
    )
    return {
        "fir_id": record.fir_id,
        "sha256_hash": record.sha256_hash,
        "status": record.status,
        "created_at": record.created_at,
        "complaint_text_saved": bool(extracted_text),
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


# ── Helper for BNS Section Detection ─────────────────────────────────────────

import re

def detect_bns_sections(text: str) -> list:
    """
    Detects BNS/IPC section references from OCR-extracted or document text generically.
    Handles common formats:
        Section 281, Sec. 281, Sec 281, Sections 281/285
        u/s 281 BNS, U/S 281/285, U/s 281, Under Section 281
        281 BNS, BNS 281, 281 IPC, IPC 281
    Returns a sorted deduplicated list of section number strings.
    """
    if not text:
        return []
    found = set()

    # 1. Matches like "Sections 281/285", "Sec. 281/285", "U/S 281/285", "u/s 281, 285", "Section 281"
    prefix_pattern = r'(?:\bsec(?:tion)?s?\.?|\bu[/\\]?s\.?|\bunder\s+sections?)\s*([0-9\(\)a-zA-Z\s/,]+)'
    for m in re.finditer(prefix_pattern, text, re.IGNORECASE):
        chunk = m.group(1)
        sec_matches = re.findall(r'\b(\d+(?:\([a-zA-Z0-9]+\))?)\b', chunk[:40])
        for sec in sec_matches:
            match_num = re.match(r'\d+', sec)
            if match_num:
                num = int(match_num.group())
                if 1 <= num <= 359:
                    found.add(sec)

    # 2. Matches like "281 BNS", "281/285 BNS", "BNS 281", "BNS 281/285", "281 IPC", "IPC 281"
    bns_pattern1 = r'\b(?:BNS|IPC)\s*([0-9\(\)a-zA-Z\s/,]+)'
    for m in re.finditer(bns_pattern1, text, re.IGNORECASE):
        chunk = m.group(1)
        sec_matches = re.findall(r'\b(\d+(?:\([a-zA-Z0-9]+\))?)\b', chunk[:40])
        for sec in sec_matches:
            match_num = re.match(r'\d+', sec)
            if match_num:
                num = int(match_num.group())
                if 1 <= num <= 359:
                    found.add(sec)

    bns_pattern2 = r'([0-9\(\)a-zA-Z\s/,]+)\s*(?:BNS|IPC)\b'
    for m in re.finditer(bns_pattern2, text, re.IGNORECASE):
        chunk = m.group(1)
        sec_matches = re.findall(r'\b(\d+(?:\([a-zA-Z0-9]+\))?)\b', chunk[-40:])
        for sec in sec_matches:
            match_num = re.match(r'\d+', sec)
            if match_num:
                num = int(match_num.group())
                if 1 <= num <= 359:
                    found.add(sec)

    def _sec_key(val: str) -> int:
        m = re.match(r'\d+', val)
        return int(m.group()) if m else 0

    return sorted(list(found), key=_sec_key)


# ── Helper for OCR Extraction ────────────────────────────────────────────────

def _extract_text_with_ocr(contents: bytes, filename: str, content_type: str) -> str:
    filename_lower = (filename or "").lower()
    content_type_lower = (content_type or "").lower()

    is_pdf = content_type_lower == "application/pdf" or filename_lower.endswith(".pdf")
    is_txt = content_type_lower in ["text/plain"] or filename_lower.endswith(".txt")
    is_image = (
        content_type_lower.startswith("image/")
        or any(filename_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"])
    )

    if not is_pdf and not is_txt and not is_image:
        raise HTTPException(
            status_code=400,
            detail="This file type can be uploaded, but LawAid cannot currently extract FIR content from this format. Please upload a PDF document, TXT file, or clear FIR image (JPG, PNG, WEBP, BMP)."
        )

    extracted_text = ""

    if is_txt:
        try:
            extracted_text = contents.decode("utf-8", errors="ignore").strip()
        except Exception:
            extracted_text = ""

    elif is_pdf:
        # 1. Native PDF text extraction with PyMuPDF
        try:
            import pymupdf
            doc = pymupdf.open(stream=contents, filetype="pdf")
            extracted_text = "\n".join([page.get_text() for page in doc]).strip()
        except Exception:
            extracted_text = ""

        # 2. If native PDF text is < 15 chars, fallback to rendering page images and OCR
        if len(extracted_text) < 15:
            try:
                import pymupdf
                from rapidocr_onnxruntime import RapidOCR
                engine = RapidOCR()
                doc = pymupdf.open(stream=contents, filetype="pdf")
                ocr_lines = []
                for page in doc:
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    result, _ = engine(img_bytes)
                    if result:
                        for line in result:
                            if line and len(line) > 1 and line[1]:
                                ocr_lines.append(str(line[1]))
                extracted_text = "\n".join(ocr_lines).strip()
            except Exception:
                pass

    elif is_image:
        # Run RapidOCR directly on image bytes
        try:
            from rapidocr_onnxruntime import RapidOCR
            engine = RapidOCR()
            result, _ = engine(contents)
            if result:
                ocr_lines = [str(line[1]) for line in result if line and len(line) > 1 and line[1]]
                extracted_text = "\n".join(ocr_lines).strip()
        except Exception:
            extracted_text = ""

    return extracted_text


@router.post("/understand")
async def understand_fir(file: UploadFile = File(...)):
    """
    Accepts an uploaded FIR (PDF, TXT, or image).
    Extracts text using PyMuPDF and/or RapidOCR, processes legal analysis via existing AI RAG pipeline,
    and returns plain-language summary, charges, entities, citizen rights, and next steps.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file is invalid or missing filename.")

    contents = await file.read()
    if not contents or len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty. Please upload a valid FIR document or image.")

    filename_lower = file.filename.lower()
    content_type_lower = (file.content_type or "").lower()

    is_pdf = content_type_lower == "application/pdf" or filename_lower.endswith(".pdf")
    is_txt = content_type_lower in ["text/plain"] or filename_lower.endswith(".txt")
    is_image = (
        content_type_lower.startswith("image/")
        or any(filename_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"])
    )

    if not is_pdf and not is_txt and not is_image:
        raise HTTPException(
            status_code=400,
            detail="This file type can be uploaded, but LawAid cannot currently extract FIR content from this format. Please upload a PDF document, TXT file, or clear FIR image (JPG, PNG, WEBP, BMP)."
        )

    # Temporary analysis processing — do NOT store file in GridFS automatically before user consent
    file_id = None
    file_stored = False

    # 2. Text extraction, OCR cleaning, and metadata extraction
    from ai.rag.parser.clean_ocr import clean_ocr_text, extract_fir_metadata
    extracted_text = _extract_text_with_ocr(contents, file.filename, file.content_type)
    cleaned_text = clean_ocr_text(extracted_text)
    ocr_meta = extract_fir_metadata(cleaned_text)
    detected_sections = detect_bns_sections(cleaned_text) if cleaned_text else []

    if not cleaned_text or len(cleaned_text.strip()) < 15:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from the uploaded document or image. Please ensure the FIR copy or photo is clear and legible."
        )

    # 3. AI Pipeline Analysis
    if not _PIPELINE_AVAILABLE:
        raise HTTPException(status_code=500, detail="AI Pipeline module not found or unavailable.")

    has_sections_in_fir = bool(detected_sections)
    sections_recorded_in_fir = detected_sections if has_sections_in_fir else []

    try:
        if has_sections_in_fir:
            ai_res = _run_pipeline(
                raw_incident=cleaned_text[:2500],
                target_sections=sections_recorded_in_fir
            )
        else:
            ai_res = _run_pipeline(
                raw_incident=cleaned_text[:2500]
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Legal Analysis failed: {str(e)}")

    charges_supported = []
    charges_uncertain = []
    full_analysis = []

    for item in ai_res.get("analysis", []):
        app_status = item.get("applicability", "supported" if item.get("status") == "Supported" else "uncertain")
        sec_str = str(item.get("section", ""))
        law_req = item.get("law_requires") or item.get("core_elements") or [item.get("title", "Statutory requirement")]
        fir_st = item.get("fir_states") or item.get("satisfied_elements") or ["Facts stated in the FIR."]
        why_apply = item.get("why_may_apply") or item.get("reasoning") or f"The allegations in the FIR correspond to the statutory scope of Section {sec_str}."
        what_uncert = item.get("what_remains_uncertain") or item.get("missing_elements") or ["Further investigation and legal proceedings required."]
        assess = item.get("assessment") or f"The allegations recorded in the FIR make Section {sec_str} relevant for consideration; the FIR itself does not establish guilt."

        entry = {
            "section": sec_str,
            "clause": item.get("clause", ""),
            "title": item.get("title", ""),
            "punishment": item.get("punishment", ""),
            "bailable": item.get("bailable", ""),
            "cognizable": item.get("cognizable", ""),
            "court": item.get("court", ""),
            "reasoning": item.get("reasoning", ""),
            "applicability": app_status,
            "status": item.get("status", ""),
            "law_requires": law_req,
            "fir_states": fir_st,
            "why_may_apply": why_apply,
            "what_remains_uncertain": what_uncert,
            "assessment": assess,
        }
        full_analysis.append(entry)

        if app_status == "supported":
            charges_supported.append(entry)
        elif app_status == "uncertain":
            charges_uncertain.append(entry)

    def _dedupe_charges(charge_list):
        seen = set()
        deduped = []
        for c in charge_list:
            sec = c.get("section", "").strip()
            if sec and sec not in seen:
                seen.add(sec)
                deduped.append(c)
        return deduped

    display_charges = _dedupe_charges(charges_supported or full_analysis)

    if has_sections_in_fir:
        explained_sections = display_charges
        potential_sections = []
    else:
        explained_sections = []
        potential_sections = display_charges

    # Build clean formatted fact summary lines from extracted metadata
    meta_summary_lines = []
    if ocr_meta.get("fir_number") != "Not stated in the FIR":
        meta_summary_lines.append(f"• FIR No.: {ocr_meta['fir_number']}")
    if ocr_meta.get("police_station") != "Not stated in the FIR":
        meta_summary_lines.append(f"• Police Station: {ocr_meta['police_station']}")
    if ocr_meta.get("district") != "Not stated in the FIR":
        meta_summary_lines.append(f"• District: {ocr_meta['district']}")
    if ocr_meta.get("date_time_of_occurrence") != "Not stated in the FIR":
        meta_summary_lines.append(f"• Date/Time of Occurrence: {ocr_meta['date_time_of_occurrence']}")
    if ocr_meta.get("place_of_occurrence") != "Not stated in the FIR":
        meta_summary_lines.append(f"• Place of Occurrence: {ocr_meta['place_of_occurrence']}")
    if ocr_meta.get("informant") != "Not stated in the FIR":
        meta_summary_lines.append(f"• Informant: {ocr_meta['informant']}")

    is_fallback = (ai_res.get("source") == "retrieval_fallback" or ai_res.get("pipeline_source") == "retrieval_fallback")

    disclaimer_note = "\n\nThese are allegations/facts recorded in the FIR. They are not, by themselves, a final determination that an offence has been proved."

    # Build clean factual narrative snippet from cleaned_text (excluding header lines)
    narrative_lines = []
    for line in cleaned_text.splitlines():
        line_s = line.strip()
        if len(line_s) > 25 and not any(line_s.lower().startswith(h) for h in ["fir no", "police station", "district", "date", "informant", "place of occurrence", "information report", "occurrence"]):
            narrative_lines.append(line_s)
        if len(narrative_lines) >= 3:
            break

    narrative_snippet = " ".join(narrative_lines) if narrative_lines else cleaned_text[:350]

    if is_fallback:
        explained_sections = []
        potential_sections = []
        display_charges = []
        # Return all retrieved candidate provisions for reference without arbitrary cap
        reference_provisions = _dedupe_charges(full_analysis or charges_uncertain)
        plain_summary = (
            "Official police complaint document recorded. Automated legal reasoning is currently in degraded fallback mode. "
            "Relevant statutory provisions retrieved from the BNS legal corpus are provided below for reference only and do NOT represent established legal findings.\n\n"
            "Key Facts Stated in FIR:\n"
            + (narrative_snippet or ("\n".join(meta_summary_lines) if meta_summary_lines else cleaned_text[:350]))
            + disclaimer_note
        )
    else:
        reference_provisions = []
        summary_base = ai_res.get("plain_summary") or ai_res.get("summary")
        if summary_base and len(summary_base.strip()) > 30 and "allegations relating to" not in summary_base.lower():
            plain_summary = summary_base.strip()
            if "These are allegations/facts recorded in the FIR" not in plain_summary:
                plain_summary += disclaimer_note
        else:
            plain_summary = (
                f"The uploaded FIR records allegations filed with law enforcement.\n\n"
                f"Summary of stated facts:\n"
                f"{narrative_snippet}\n"
                + disclaimer_note
            )

    what_alleges = ai_res.get("what_fir_alleges")
    if not what_alleges or len(what_alleges.strip()) < 20 or "the place of occurrence" in what_alleges.lower() or "'s details" in what_alleges.lower():
        factual_clause_parts = []
        if ocr_meta.get("informant") != "Not stated in the FIR":
            factual_clause_parts.append(f"by informant {ocr_meta['informant']}")
        if ocr_meta.get("place_of_occurrence") != "Not stated in the FIR":
            factual_clause_parts.append(f"at {ocr_meta['place_of_occurrence']}")
        if ocr_meta.get("date_time_of_occurrence") != "Not stated in the FIR":
            factual_clause_parts.append(f"on or about {ocr_meta['date_time_of_occurrence']}")

        clause_str = (" " + ", ".join(factual_clause_parts)) if factual_clause_parts else ""
        what_alleges = (
            f"According to the FIR recorded{clause_str}, the report alleges: {narrative_snippet}. "
            "These statements represent claims filed with law enforcement for official investigation."
        )

    # Dynamic case-relevant fallbacks for unestablished facts and clarifying details
    offence_titles_lower = " ".join([c.get("title", "").lower() for c in display_charges])
    
    if "driving" in offence_titles_lower or "riding" in offence_titles_lower or "road" in cleaned_text.lower() or "accident" in cleaned_text.lower():
        default_unestablished = [
            "Whether the vehicle was operated in a rash or negligent manner at excessive speed.",
            "Whether mechanical failure or road conditions contributed to the incident.",
            "Medical findings and formal injury certificates of involved parties."
        ]
        default_clarifying = [
            "Are there eyewitness statements or CCTV recordings of the vehicle's movement?",
            "Was a formal motor vehicle inspector's technical report prepared?"
        ]
    elif "theft" in offence_titles_lower or "stolen" in cleaned_text.lower():
        default_unestablished = [
            "Whether the property was taken without consent with dishonest intent.",
            "Ownership documentation and valuation proof of the reported property.",
            "Recovery status of the reported item."
        ]
        default_clarifying = [
            "Was the property in the personal custody of the victim or in a public location?",
            "What was the estimated valuation of the item?"
        ]
    elif "hurt" in offence_titles_lower or "assault" in offence_titles_lower or "injury" in cleaned_text.lower():
        default_unestablished = [
            "Nature, classification, and medical severity of physical injuries.",
            "Whether dangerous weapons or means were used during the alleged conduct."
        ]
        default_clarifying = [
            "Is a Medico-Legal Certificate (MLC) or hospital record available?",
            "Were any weapons or dangerous instruments alleged to be used?"
        ]
    else:
        default_unestablished = [
            "Whether the allegations stated in the FIR are ultimately proved through investigation.",
            "Whether the accused possessed the required statutory criminal intent or knowledge.",
            "Witness statements and formal evidentiary findings."
        ]
        default_clarifying = [
            "Are there medical reports, receipts, digital evidence, or CCTV recordings supporting the timeline?",
            "Were there independent witnesses present at the scene?"
        ]

    unestablished = ai_res.get("unestablished_facts") or default_unestablished
    clarifying = ai_res.get("clarifying_details") or default_clarifying

    rights = ai_res.get("rights") or [
        "Under Section 173(2) BNSS, right to receive a free copy of the First Information Report (FIR) immediately.",
        "Under Article 22(1) of the Constitution and Section 47 BNSS, right to consult and be defended by legal counsel of choice.",
        "Under Article 22(2) of the Constitution and Section 57 BNSS, right not to be detained in police custody beyond 24 hours without production before a Magistrate.",
        "Under Article 39A of the Constitution, right to free legal aid through the Legal Services Authority if unable to afford counsel."
    ]

    next_steps = ai_res.get("next_steps") or [
        "Preserve physical and digital copies of the FIR document.",
        "Verify dates, times, vehicle numbers, and witness details mentioned in the report.",
        "Obtain and preserve medical reports, receipts, digital evidence, or CCTV footage where applicable.",
        "Identify witnesses mentioned in the FIR and seek legal assistance based on your role (informant/victim/accused)."
    ]

    if has_sections_in_fir:
        bottom_line_val = ai_res.get("bottom_line") or (
            f"This FIR explicitly states allegations under Section {', '.join(sections_recorded_in_fir)}. "
            "These provisions are relevant for legal consideration; the FIR itself does not establish guilt."
        )
    else:
        active_secs = [c["section"] for c in display_charges if c.get("section")]
        sec_label = f"Section {', '.join(active_secs)}" if active_secs else "the relevant BNS provisions"
        bottom_line_val = ai_res.get("bottom_line") or (
            f"Based on the facts recorded in this FIR, {sec_label} appears potentially relevant for consideration. "
            "The FIR itself does not explicitly record an offence section number, nor does it establish that the offence has been proved."
        )

    disclaimer_text = ai_res.get(
        "disclaimer",
        "Legal analysis provided by LawAid AI is for informational and educational purposes only. It does not constitute formal legal advice or substitute for consultation with a qualified legal professional."
    )

    return {
        "status": "ok" if not is_fallback else "degraded_fallback",
        "is_degraded_fallback": is_fallback,
        "file_id": file_id,
        "file_stored": file_stored,
        "filename": file.filename,
        "extracted_text": cleaned_text[:1200],
        "ocr_metadata": ocr_meta,
        "sections_recorded_in_fir": sections_recorded_in_fir,
        "has_sections_in_fir": has_sections_in_fir,
        "explained_sections": explained_sections,
        "potential_sections": potential_sections,
        "charges": display_charges,
        "detected_sections": sections_recorded_in_fir,
        "entities": ai_res.get("privacy_metadata", {}).get("detections", []),
        "summary": plain_summary,
        "what_fir_alleges": what_alleges,
        "reference_provisions": reference_provisions,
        "uncertain_provisions": charges_uncertain if not is_fallback else [],
        "analysis": full_analysis,
        "unestablished_facts": unestablished,
        "clarifying_details": clarifying,
        "rights": rights,
        "next_steps": next_steps,
        "bottom_line": bottom_line_val,
        "disclaimer": disclaimer_text,
    }


# ── Saved FIRs (Citizen Opt-In Persistence) ───────────────────────────────────

import json
from app.models.saved_fir import SavedFIR


from typing import Optional, List, Any

class SaveFIRRequest(BaseModel):
    filename: str = "fir_document.pdf"
    file_type: Optional[str] = "application/pdf"
    file_size: Optional[int] = 0
    file_id: Optional[str] = None        # optional existing GridFS file ID
    file_base64: Optional[str] = None    # optional base64 encoded file for GridFS storage on explicit user consent
    extracted_text: Optional[str] = ""
    summary: Optional[str] = "FIR Analysis"
    charges: Optional[List[Any]] = []
    reference_provisions: Optional[List[Any]] = []
    rights: Optional[List[Any]] = []
    next_steps: Optional[List[Any]] = []
    disclaimer: Optional[str] = ""


@router.post("/saved")
def save_fir_analysis(
    body: SaveFIRRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Persists an analyzed FIR to the citizen's account after explicit user consent.
    If file_base64 is provided, stores the document binary in GridFS as part of the consent flow.
    """
    gridfs_id = body.file_id
    if not gridfs_id and body.file_base64:
        from app.core.mongo import mongo_available, fs as _mongo_fs
        if mongo_available and _mongo_fs is not None:
            try:
                import base64
                file_bytes = base64.b64decode(body.file_base64)
                # Sanitize filename before storing in GridFS
                safe_filename = Path(body.filename).name if body.filename else "fir_document.pdf"
                gridfs_id = str(_mongo_fs.put(
                    file_bytes,
                    filename=safe_filename,
                    content_type=body.file_type or "application/pdf"
                ))
            except Exception:
                gridfs_id = None

    saved_record = SavedFIR(
        user_id=current_user.id,
        filename=Path(body.filename).name if body.filename else "fir_document",
        file_type=body.file_type,
        file_size=body.file_size,
        gridfs_file_id=gridfs_id,
        extracted_text=body.extracted_text,
        summary=body.summary,
        charges=json.dumps(body.charges),
        reference_provisions=json.dumps(body.reference_provisions),
        rights=json.dumps(body.rights),
        next_steps=json.dumps(body.next_steps),
        disclaimer=body.disclaimer
    )
    db.add(saved_record)
    db.commit()
    db.refresh(saved_record)
    return {
        "status": "saved",
        "saved_id": saved_record.id,
        "filename": saved_record.filename,
        "gridfs_file_id": gridfs_id,
        "created_at": saved_record.created_at
    }


@router.get("/saved")
def get_saved_firs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all saved FIR analyses belonging to the authenticated user.
    """
    records = (
        db.query(SavedFIR)
        .filter(SavedFIR.user_id == current_user.id)
        .order_by(SavedFIR.created_at.desc())
        .all()
    )
    result = []
    for r in records:
        r_dict = {
            "id": r.id,
            "filename": r.filename,
            "file_type": r.file_type,
            "file_size": r.file_size,
            "gridfs_file_id": r.gridfs_file_id,
            "summary": r.summary,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        try:
            r_dict["charges"] = json.loads(r.charges) if r.charges else []
        except Exception:
            r_dict["charges"] = []
        try:
            r_dict["reference_provisions"] = json.loads(r.reference_provisions) if r.reference_provisions else []
        except Exception:
            r_dict["reference_provisions"] = []
        try:
            r_dict["rights"] = json.loads(r.rights) if r.rights else []
        except Exception:
            r_dict["rights"] = []
        try:
            r_dict["next_steps"] = json.loads(r.next_steps) if r.next_steps else []
        except Exception:
            r_dict["next_steps"] = []
        result.append(r_dict)
    return result


@router.get("/saved/{saved_id}")
def get_saved_fir_detail(
    saved_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a single saved FIR analysis belonging to the authenticated user.
    """
    record = db.query(SavedFIR).filter(SavedFIR.id == saved_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Saved FIR not found.")
    if record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this saved FIR.")

    r_dict = {
        "id": record.id,
        "filename": record.filename,
        "file_type": record.file_type,
        "file_size": record.file_size,
        "gridfs_file_id": record.gridfs_file_id,
        "extracted_text": record.extracted_text,
        "summary": record.summary,
        "disclaimer": record.disclaimer,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    try:
        r_dict["charges"] = json.loads(record.charges) if record.charges else []
    except Exception:
        r_dict["charges"] = []
    try:
        r_dict["reference_provisions"] = json.loads(record.reference_provisions) if record.reference_provisions else []
    except Exception:
        r_dict["reference_provisions"] = []
    try:
        r_dict["rights"] = json.loads(record.rights) if record.rights else []
    except Exception:
        r_dict["rights"] = []
    try:
        r_dict["next_steps"] = json.loads(record.next_steps) if record.next_steps else []
    except Exception:
        r_dict["next_steps"] = []

    return r_dict


@router.delete("/saved/{saved_id}")
def delete_saved_fir(
    saved_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a saved FIR record, analysis, and GridFS stored document from active application storage.
    Enforces server-side ownership.
    """
    record = db.query(SavedFIR).filter(SavedFIR.id == saved_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Saved FIR not found.")
    if record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this saved FIR.")

    # Remove associated GridFS stored document if present
    if record.gridfs_file_id:
        from app.core.mongo import mongo_available, fs as _mongo_fs
        if mongo_available and _mongo_fs is not None:
            try:
                from bson import ObjectId
                _mongo_fs.delete(ObjectId(record.gridfs_file_id))
            except Exception:
                pass

    db.delete(record)
    db.commit()
    return {"status": "deleted", "saved_id": saved_id}


class FIRGenerateRequest(BaseModel):
    complaint: str
    station_code: str = "PS001"
    district: str = "Central"
    complainant_name: str = "Protected / Citizen"


@router.post("/generate")
def generate_fir(body: FIRGenerateRequest = None):
    """
    Generates a formal First Information Report (FIR) draft as a PDF.
    Returns official FIR ID (UUID4-based), SHA-256 hash, and download URL.
    """
    import hashlib
    import uuid
    import datetime
    import io
    import textwrap
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation module (reportlab) not installed. Run: pip install reportlab")

    now = datetime.datetime.now()
    year = now.year

    # UUID4-based FIR ID — unpredictable and globally unique
    fir_uuid = uuid.uuid4().hex[:8].upper()
    fir_id = f"FIR/{year}/{fir_uuid}"

    complaint_text = body.complaint if body and body.complaint else "General complaint lodged."
    complainant_name = body.complainant_name if body and body.complainant_name else "Protected / Citizen"
    station_code = body.station_code if body else "PS001"

    # Build PDF in memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "FIRST INFORMATION REPORT (FIR)")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 80, f"FIR ID: {fir_id}")
    c.drawString(50, height - 100, f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(50, height - 120, f"Police Station: {station_code}")
    c.drawString(50, height - 140, f"Complainant: {complainant_name}")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, height - 170, "Incident Description:")
    c.setFont("Helvetica", 10)

    lines = textwrap.wrap(complaint_text, width=85)
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

    # Store in MongoDB/GridFS — report honestly whether it succeeded
    from app.core.mongo import mongo_available, fs as _mongo_fs
    file_id = None
    file_stored = False
    if mongo_available and _mongo_fs is not None:
        try:
            file_id = str(_mongo_fs.put(
                pdf_bytes,
                filename=f"{fir_id.replace('/', '_')}.pdf",
                content_type="application/pdf",
                metadata={"fir_id": fir_id, "sha256_hash": sha256_hash}
            ))
            file_stored = True
        except Exception:
            file_id = None
            file_stored = False

    return {
        "fir_id": fir_id,
        "status": "draft_created",
        "sha256_hash": sha256_hash,
        "created_at": now.isoformat(),
        "station_code": station_code,
        "district": body.district if body else "Central",
        "file_stored": file_stored,
        "pdf_url": f"/api/fir/download/{file_id}" if file_id else None,
        "summary": f"Draft FIR registered under ID {fir_id}. Ready for official review and station stamp.",
    }


from fastapi.responses import StreamingResponse

@router.get("/download/{file_id}")
def download_fir(file_id: str):
    """Download a stored FIR PDF from MongoDB/GridFS."""
    from app.core.mongo import mongo_available, fs as _mongo_fs
    if not mongo_available or _mongo_fs is None:
        raise HTTPException(
            status_code=503,
            detail="File storage (MongoDB) is unavailable. Cannot retrieve files."
        )
    from bson.objectid import ObjectId
    try:
        file_data = _mongo_fs.get(ObjectId(file_id))
        return StreamingResponse(
            file_data,
            media_type=file_data.content_type or "application/pdf",
            headers={"Content-Disposition": f"attachment; filename={file_data.filename}"}
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found or invalid file ID.")


@router.get("/{fir_id}")
def get_fir(fir_id: str, db: Session = Depends(get_db)):
    from app.models.fir_registry import FIRRegistry
    record = db.query(FIRRegistry).filter(FIRRegistry.fir_id == fir_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="FIR not found")
    
    return {
        "fir_id": record.fir_id,
        "sha256_hash": record.sha256_hash,
        "officer_id": record.officer_id,
        "station_code": record.station_code,
        "status": record.status,
        "created_at": record.created_at,
        "complaint_text": record.complaint_text,
    }


# ── Duplicate Check ──────────────────────────────────────────────────────────

class DuplicateCheckRequest(BaseModel):
    complaint_text: str


@router.post("/check-duplicate")
def check_duplicate_route(body: DuplicateCheckRequest, db: Session = Depends(get_db)):
    """
    Checks whether a complaint is likely a duplicate of an existing FIR.
    Accepts a JSON body { complaint_text } (not a query parameter).
    """
    result = check_duplicate(db, body.complaint_text)
    return result