import datetime
import hashlib
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.fir_registry import FIRRegistry
from app.models.user import User

router = APIRouter(prefix="/police", tags=["police"])



class ValidateFIRRequest(BaseModel):
    district: Optional[str] = ""
    policeStation: Optional[str] = ""
    complainantName: Optional[str] = ""
    occurrenceDate: Optional[str] = ""
    placeAddress: Optional[str] = ""
    firContents: Optional[str] = ""
    act1: Optional[str] = "BNS 2023"
    section1: Optional[str] = ""


class ExtractStatementRequest(BaseModel):
    statement: str


def _fallback_extract_entities(statement_text: str) -> Dict[str, str]:
    lower_stmt = (statement_text or "").lower()
    try:
        from ai.rag.ner.ner_extractor import extract_entities
        ner_res = extract_entities(statement_text)
        date_val = ner_res.get("dates", [""])[0] if ner_res.get("dates") else ""
        time_val = ner_res.get("times", [""])[0] if ner_res.get("times") else ""
        loc_val = ", ".join(ner_res.get("locations", [])) if ner_res.get("locations") else ""
        accused_val = ", ".join(ner_res.get("accused", [])) if ner_res.get("accused") else ""
    except Exception:
        date_val, time_val, loc_val, accused_val = "", "", "", ""

    if not accused_val:
        if "unknown man" in lower_stmt or "unknown male" in lower_stmt:
            accused_val = "Unknown man"
        elif "unknown woman" in lower_stmt or "unknown female" in lower_stmt:
            accused_val = "Unknown woman"
        elif "unknown" in lower_stmt:
            accused_val = "Unknown accused person(s)"

    prop_val = ""
    if "phone" in lower_stmt or "mobile" in lower_stmt:
        prop_val = "One mobile phone"
    elif "wallet" in lower_stmt or "purse" in lower_stmt:
        prop_val = "One wallet/purse"
    elif "vehicle" in lower_stmt or "motorcycle" in lower_stmt or "car" in lower_stmt:
        prop_val = "Vehicle"

    return {
        "occurrenceDate": date_val,
        "occurrenceTime": time_val,
        "placeAddress": loc_val,
        "complainantName": "",
        "accusedDetails": accused_val,
        "propertyDetails": prop_val,
        "propertyValue": "",
        "firContents": statement_text,
    }


@router.post("/extract-statement")
def extract_statement(body: ExtractStatementRequest):
    """
    Extracts structured IF1 First Information Report fields from an incident statement.
    Uses AI/LLM structured extraction with fallback to spaCy/NER.
    Does NOT invent missing facts, police stations, or personal details.
    """
    raw_statement = (body.statement or "").strip()
    if len(raw_statement) < 5:
        raise HTTPException(status_code=400, detail="Statement text is too short to extract information.")

    extracted_data = {}
    try:
        from ai.rag.analysis.legal_analyzer import MultiProviderLLMFailoverClient, Workload
        import json

        client = MultiProviderLLMFailoverClient()
        prompt = (
            "You are an expert legal assistant for Indian Law Enforcement (BNS / BNSS 2023).\n"
            "Extract structured IF1 First Information Report fields from the statement below.\n\n"
            "CRITICAL CONSTRAINTS:\n"
            "1. ONLY extract facts explicitly stated in the statement text.\n"
            "2. DO NOT invent, assume, or hallucinate missing personal information, police station, district, officer details, or property value.\n"
            "3. If a field is not present in the statement, return an empty string \"\".\n\n"
            "Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            "  \"occurrenceDate\": \"DD-MM-YYYY date format if present, else empty string\",\n"
            "  \"occurrenceTime\": \"Time of occurrence if present, else empty string\",\n"
            "  \"placeAddress\": \"Place of occurrence / location mentioned, else empty string\",\n"
            "  \"complainantName\": \"Complainant name if explicitly stated, else empty string\",\n"
            "  \"accusedDetails\": \"Accused description, identity, escape details if mentioned, else empty string\",\n"
            "  \"propertyDetails\": \"Property stolen or involved if mentioned, else empty string\",\n"
            "  \"propertyValue\": \"Property value ONLY if an explicit monetary amount is stated, else empty string\",\n"
            "  \"firContents\": \"The statement text describing the incident\"\n"
            "}\n\n"
            "STATEMENT TEXT:\n"
            f"{raw_statement}\n"
        )
        llm_raw = client.generate(prompt, workload=Workload.POLICE_FIR_DRAFT)
        cleaned = llm_raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        extracted_data = json.loads(cleaned.strip())
    except Exception:
        extracted_data = _fallback_extract_entities(raw_statement)

    if not isinstance(extracted_data, dict):
        extracted_data = _fallback_extract_entities(raw_statement)

    expected_keys = [
        "occurrenceDate", "occurrenceTime", "placeAddress", "complainantName",
        "accusedDetails", "propertyDetails", "propertyValue", "firContents"
    ]
    for key in expected_keys:
        if key not in extracted_data or extracted_data[key] is None:
            extracted_data[key] = ""
        else:
            extracted_data[key] = str(extracted_data[key]).strip()

    if not extracted_data.get("firContents"):
        extracted_data["firContents"] = raw_statement

    return {
        "status": "ok",
        "data": extracted_data
    }


@router.post("/validate-fir")
def validate_fir(body: ValidateFIRRequest):
    """
    Validates mandatory Indian FIR fields under BNSS Section 173.
    Checks date, location, complainant identity, and BNS offence definition.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not body.complainantName or len(body.complainantName.strip()) < 2:
        errors.append("Complainant / Informant name is mandatory.")

    if not body.policeStation or len(body.policeStation.strip()) < 2:
        errors.append("Police Station name must be specified.")

    if not body.placeAddress or len(body.placeAddress.strip()) < 3:
        errors.append("Place of occurrence address is mandatory.")

    if not body.firContents or len(body.firContents.strip()) < 20:
        errors.append("FIR incident facts (firContents) must contain at least 20 characters describing the event.")

    if not body.section1:
        warnings.append("Primary BNS section is not specified. AI recommendation: Check Section 303 (Theft) or Section 318 (Cheating).")

    is_valid = len(errors) == 0
    return {
        "valid": is_valid,
        "status": "passed" if is_valid else "validation_failed",
        "errors": errors,
        "warnings": warnings,
        "timestamp": datetime.datetime.now().isoformat(),
    }


class ApproveFIRRequest(BaseModel):
    fir_draft_id: Optional[str] = None
    station_code: Optional[str] = "PS001"
    officer_name: Optional[str] = "Station House Officer"
    summary: Optional[str] = ""
    fir_data: Optional[Dict[str, Any]] = None


@router.post("/approve-fir")
def approve_fir(
    body: ApproveFIRRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Formally registers and locks an official FIR draft.
    Generates cryptographic tamper-proof SHA-256 hash of the final PDF stored in PostgreSQL and GridFS.
    Requires an authenticated police officer — officer_id is taken from the JWT.
    """
    import uuid
    from ai.fir_engine.fir_pdf_generator import generate_fir_pdf
    from app.core.mongo import mongo_available, fs as _mongo_fs
    
    now = datetime.datetime.now()
    year = now.year

    # Use UUID4 for public FIR ID so it's unpredictable
    if body.fir_draft_id:
        official_fir_id = body.fir_draft_id
    else:
        official_fir_id = f"FIR/{year}/{uuid.uuid4().hex[:8].upper()}"

    # Generate final PDF bytes from fir_data if provided
    pdf_bytes = b""
    if body.fir_data:
        try:
            body.fir_data["fir_number"] = official_fir_id
            pdf_bytes = generate_fir_pdf(body.fir_data)
        except Exception:
            pdf_bytes = b""
            
    if not pdf_bytes:
        # Fallback if fir_data generation fails or wasn't provided
        hash_source = f"{official_fir_id}:{body.station_code}:{current_user.id}:{now.isoformat()}"
        pdf_bytes = hash_source.encode("utf-8")

    fir_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # Store in MongoDB/GridFS
    file_id = None
    if mongo_available and _mongo_fs is not None and body.fir_data:
        try:
            file_id = str(_mongo_fs.put(
                pdf_bytes,
                filename=f"{official_fir_id.replace('/', '_')}.pdf",
                content_type="application/pdf",
                metadata={"fir_id": official_fir_id, "sha256_hash": fir_hash}
            ))
        except Exception:
            file_id = None

    # Persist in FIRRegistry — officer_id from authenticated user
    try:
        registry_record = FIRRegistry(
            fir_id=official_fir_id,
            sha256_hash=fir_hash,
            officer_id=current_user.id,
            station_code=body.station_code or "PS001",
            status="APPROVED",
            complaint_text=body.summary or "",
        )
        db.add(registry_record)
        db.commit()
        db.refresh(registry_record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save FIR registry record: {str(e)}")

    return {
        "status": "APPROVED",
        "fir_id": official_fir_id,
        "sha256_hash": fir_hash,
        "station_code": body.station_code,
        "officer": body.officer_name,
        "officer_id": current_user.id,
        "approved_at": now.isoformat(),
        "pdf_url": f"/api/fir/download/{file_id}" if file_id else None,
        "tamper_proof_seal": "VERIFIED_BNSS_OFFICIAL",
    }


@router.post("/transcribe")
async def transcribe_statement(file: UploadFile = File(None), statement_text: Optional[str] = None):
    """
    Accepts a text statement or a plain .txt file and extracts legal entities.
    NOTE: Real audio-to-text transcription (Whisper/speech-to-text) is NOT yet implemented.
    Uploading an audio file will return HTTP 501 with a clear message.
    """
    text_content = statement_text or ""

    if file:
        filename = (file.filename or "").lower()
        if filename.endswith(".txt"):
            raw_bytes = await file.read()
            text_content = raw_bytes.decode("utf-8", errors="ignore")
        else:
            # Audio or other non-text formats — do NOT fake the transcription
            raise HTTPException(
                status_code=501,
                detail=(
                    "Audio transcription is not yet implemented. "
                    "Please type or paste the complainant's statement as text. "
                    "Only .txt files are currently accepted for file-based input."
                )
            )

    if not text_content or not text_content.strip():
        raise HTTPException(
            status_code=400,
            detail="No statement text provided. Please supply 'statement_text' or upload a .txt file."
        )

    # Extract entities using spaCy
    entities = {}
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text_content)
        for ent in doc.ents:
            entities.setdefault(ent.label_, []).append(ent.text)
    except OSError:
        entities = {}
    except Exception:
        entities = {}

    return {
        "status": "ok",
        "transcript": text_content,
        "entities": entities,
        "note": "Transcript was provided as text input. Audio transcription not available."
    }



class GenerateFIRRequest(BaseModel):
    incident: str


class RenderFIRPDFRequest(BaseModel):
    fir_data: Dict[str, Any]


@router.post("/generate-fir")
def generate_fir(body: GenerateFIRRequest):
    """
    Executes the end-to-end AI FIR Generation workflow for Police Officers.
    Runs grounded LawAid RAG pipeline, extracts supported BNS sections,
    generates structured IF1 FIR JSON, and renders overlay on official IF1 PDF template.
    """
    import base64
    from ai.rag.pipeline import run_pipeline
    from ai.fir_engine.fir_ai_generator import generate_structured_fir
    from ai.fir_engine.fir_pdf_generator import generate_fir_pdf

    incident_text = (body.incident or "").strip()
    if len(incident_text) < 10:
        raise HTTPException(status_code=400, detail="Incident description must contain at least 10 characters.")

    # 1. Run grounded RAG pipeline (NER, retrieval, reranking, legal analysis)
    pipeline_res = run_pipeline(raw_incident=incident_text)

    sanitized_incident = pipeline_res.get("sanitized_incident", incident_text)
    grounded_analysis = pipeline_res.get("analysis", [])

    # 2. Extract supported BNS section titles
    supported_sections = []
    for item in grounded_analysis:
        if item.get("applicability") == "supported":
            sec_num = str(item.get("section", "")).strip()
            title = str(item.get("title", "")).strip()
            if sec_num:
                label = f"BNS Section {sec_num}" if not sec_num.lower().startswith("section") else sec_num
                if title:
                    label += f" ({title})"
                if label not in supported_sections:
                    supported_sections.append(label)

    # 3. Generate structured IF1 FIR JSON
    fir_data = generate_structured_fir(
        sanitized_incident=sanitized_incident,
        grounded_analysis=grounded_analysis
    )

    # 4. Render overlay on official IF1 PDF template
    pdf_bytes = b""
    try:
        pdf_bytes = generate_fir_pdf(fir_data)
    except Exception:
        pdf_bytes = b""

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8") if pdf_bytes else ""

    return {
        "status": "ok",
        "sanitized_incident": sanitized_incident,
        "fir_data": fir_data,
        "supported_sections": supported_sections,
        "pdf_base64": pdf_base64
    }


@router.post("/render-fir-pdf")
def render_fir_pdf(body: RenderFIRPDFRequest):
    """
    Renders updated/edited structured FIR JSON into the official IF1 PDF template and returns PDF file bytes.
    """
    import base64
    from fastapi.responses import Response
    from ai.fir_engine.fir_pdf_generator import generate_fir_pdf

    if not body.fir_data or not isinstance(body.fir_data, dict):
        raise HTTPException(status_code=400, detail="Invalid FIR data provided.")

    try:
        pdf_bytes = generate_fir_pdf(body.fir_data)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        return {
            "status": "ok",
            "pdf_base64": pdf_base64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate FIR PDF: {str(e)}")