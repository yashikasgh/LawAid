import json
from io import BytesIO
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.case_document import CaseDocument
from app.models.lawyer_case import LawyerCase
from app.models.lawyer_workflow import CaseAnalysis, CaseSummary, CaseTimelineEvent
from app.models.user import User
from app.services.lawyer_case_analysis import extract_case_information

router = APIRouter(prefix="/lawyer", tags=["lawyer-workflow"])
EVENT_TYPES = {"Incident", "Police Complaint", "FIR", "Medical", "Witness Statement", "Investigation", "Charge Sheet", "Court Proceedings"}

def _case(case_id, user, db):
    value = db.query(LawyerCase).filter(LawyerCase.id == case_id, LawyerCase.lawyer_id == user.id).first()
    if not value: raise HTTPException(404, "Case not found")
    return value
def _loads(value, fallback):
    try: return json.loads(value or "")
    except (TypeError, json.JSONDecodeError): return fallback
def _analysis(case_id, db): return db.query(CaseAnalysis).filter(CaseAnalysis.case_id == case_id).first()
def _serialize_event(e):
    source_reference = _loads(e.source_reference, None)
    return {"id": e.id, "date": e.event_date, "time": e.event_time, "title": e.title, "description": e.description, "event_type": e.event_type, "source_document_id": e.source_document_id, "source_document_name": (source_reference or {}).get("document_name"), "related_bns_sections": _loads(e.related_bns_sections, []), "source_reference": source_reference, "confidence": e.confidence, "is_edited": e.is_edited == "true"}
def _timeline(case_id, db): return db.query(CaseTimelineEvent).filter(CaseTimelineEvent.case_id == case_id).order_by(CaseTimelineEvent.event_date, CaseTimelineEvent.event_time).all()

class AnalysisPatch(BaseModel):
    payload: dict
class EventPatch(BaseModel):
    date: str | None = None; time: str | None = None; title: str | None = Field(default=None, max_length=300); description: str | None = None; event_type: str | None = None
class SummaryPatch(BaseModel):
    executive_summary: str = Field(max_length=20000); current_stage: str | None = Field(default=None, max_length=120)
class ExportOptions(BaseModel):
    include_executive_summary: bool = True; include_timeline: bool = True; include_key_facts: bool = True; include_bns_sections: bool = True; include_original_documents: bool = True

@router.get("/cases/{case_id}")
def get_case(case_id: str, current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)):
    case = _case(case_id, current_user, db)
    return {"id": case.id, "case_number": case.id, "title": case.title, "created_at": case.created_at, "updated_at": case.updated_at}

@router.post("/cases/{case_id}/analyze")
def analyze(case_id: str, current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)):
    _case(case_id, current_user, db)
    documents = db.query(CaseDocument).filter(CaseDocument.case_id == case_id).all()
    if not documents or any(d.status != "parsed" for d in documents): raise HTTPException(409, "All selected documents must finish parsing before analysis can start.")
    record = _analysis(case_id, db) or CaseAnalysis(case_id=case_id); db.add(record); record.status = "processing"; record.error_message = None; db.commit()
    try:
        payload = extract_case_information(documents)
        record.payload = json.dumps(payload); record.status = "completed"
        db.query(CaseTimelineEvent).filter(CaseTimelineEvent.case_id == case_id, CaseTimelineEvent.is_edited == "false").delete(synchronize_session=False)
        for candidate in payload["timeline_candidates"]:
            db.add(CaseTimelineEvent(case_id=case_id, source_document_id=candidate["source_document_id"], event_date=candidate["date"], event_time=candidate["time"], title=candidate["title"], description=candidate["description"], event_type=candidate["event_type"], source_reference=json.dumps(candidate["source_reference"]), confidence=candidate["confidence"]))
        db.commit(); return {"status": "completed", "analysis": payload}
    except Exception:
        db.rollback(); record = _analysis(case_id, db) or CaseAnalysis(case_id=case_id); db.add(record); record.status="failed"; record.error_message="Analysis could not be completed. Retry after checking parsed documents."; db.commit(); raise HTTPException(503, "Analysis could not be completed. Retry later.")

@router.get("/cases/{case_id}/analysis")
def get_analysis(case_id: str, current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)):
    _case(case_id, current_user, db); record = _analysis(case_id, db)
    if not record: return {"status": "pending", "analysis": None, "error": None}
    return {"status": record.status, "analysis": _loads(record.payload, {}), "error": record.error_message}
@router.patch("/cases/{case_id}/analysis")
def update_analysis(case_id: str, body: AnalysisPatch, current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)):
    _case(case_id, current_user, db); record = _analysis(case_id, db)
    if not record: raise HTTPException(409, "Run analysis before saving corrections.")
    record.payload = json.dumps(body.payload); record.status="completed"; record.error_message=None; db.commit(); return {"status": "completed", "analysis": body.payload, "edited": True}

@router.get("/cases/{case_id}/timeline")
def get_timeline(case_id: str, event_type: str | None = None, source_document_id: str | None = None, date_from: str | None = None, date_to: str | None = None, order: str = "oldest", current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)):
    _case(case_id, current_user, db); values = _timeline(case_id, db)
    if event_type: values = [e for e in values if e.event_type == event_type]
    if source_document_id: values = [e for e in values if e.source_document_id == source_document_id]
    if date_from: values = [e for e in values if e.event_date >= date_from]
    if date_to: values = [e for e in values if e.event_date <= date_to]
    data = [_serialize_event(e) for e in values]; data.sort(key=lambda e: (e["date"], e["time"] or ""), reverse=order == "newest"); return data
@router.patch("/cases/{case_id}/timeline/{event_id}")
def update_timeline(case_id: str, event_id: str, body: EventPatch, current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)):
    _case(case_id, current_user, db); event = db.query(CaseTimelineEvent).filter(CaseTimelineEvent.id == event_id, CaseTimelineEvent.case_id == case_id).first()
    if not event: raise HTTPException(404, "Timeline event not found")
    if body.event_type is not None and body.event_type not in EVENT_TYPES: raise HTTPException(422, "Unsupported timeline event type")
    for field, value in body.model_dump(exclude_unset=True).items(): setattr(event, "event_" + field if field in {"date", "time", "type"} else field, value)
    event.is_edited="true"; db.commit(); db.refresh(event); return _serialize_event(event)

def _summary(case_id, db): return db.query(CaseSummary).filter(CaseSummary.case_id == case_id).first()
@router.get("/cases/{case_id}/summary")
def get_summary(case_id: str, current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)):
    case = _case(case_id, current_user, db); record = _summary(case_id, db); data = _loads((_analysis(case_id, db) or CaseAnalysis(payload="{}")).payload, {})
    return {"case_id": case_id, "case_number": case_id, "current_stage": record.current_stage if record else None, "executive_summary": record.executive_summary if record else "", "key_facts": data.get("key_facts", []), "bns_sections": data.get("bns_sections", []), "timeline_preview": [_serialize_event(e) for e in _timeline(case_id, db)[:5]]}
@router.patch("/cases/{case_id}/summary")
def update_summary(case_id: str, body: SummaryPatch, current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)):
    _case(case_id, current_user, db); record = _summary(case_id, db) or CaseSummary(case_id=case_id); db.add(record); record.executive_summary=body.executive_summary; record.current_stage=body.current_stage; db.commit(); return get_summary(case_id, current_user, db)

@router.post("/cases/{case_id}/export")
def export_case(case_id: str, options: ExportOptions, current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)):
    def _esc(t): return escape(str(t or "")).encode("ascii", "xmlcharrefreplace").decode("ascii")
    summary = get_summary(case_id, current_user, db); documents = db.query(CaseDocument).filter(CaseDocument.case_id == case_id).all(); stream=BytesIO(); styles=getSampleStyleSheet(); story=[Paragraph("LawAid Case Package", styles["Title"])]
    if options.include_executive_summary: story += [Paragraph("Executive Summary", styles["Heading2"]), Paragraph(_esc(summary["executive_summary"] or "Not provided."), styles["BodyText"])]
    if options.include_timeline:
        story.append(Paragraph("Case Timeline", styles["Heading2"])); story += [Paragraph(_esc(f"{e.event_date} {e.title}: {e.description}"), styles["BodyText"]) for e in _timeline(case_id, db)]
    if options.include_key_facts: story += [Paragraph("Key Facts", styles["Heading2"])] + [Paragraph(_esc(f.get("text", "")), styles["BodyText"]) for f in summary["key_facts"]]
    if options.include_bns_sections: story += [Paragraph("Potential BNS Sections", styles["Heading2"])] + [Paragraph(_esc(f"Section {s['section_number']} (source-linked; requires legal review)"), styles["BodyText"]) for s in summary["bns_sections"]]
    if options.include_original_documents: story += [Paragraph("Original Document Appendix", styles["Heading2"])] + [Paragraph(_esc(f"{d.original_filename} ({d.status})"), styles["BodyText"]) for d in documents]
    SimpleDocTemplate(stream, pagesize=A4).build(story); stream.seek(0); return StreamingResponse(stream, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="case-package-{case_id}.pdf"'})
