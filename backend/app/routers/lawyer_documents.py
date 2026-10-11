import hashlib
import json
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.core.mongo import fs, mongo_available
from app.models.case_document import CaseDocument
from app.models.lawyer_case import LawyerCase
from app.models.user import User
from app.services.case_document_parser import parse_case_document

router = APIRouter(prefix="/lawyer", tags=["lawyer-documents"])

MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}
WORKSPACE_TITLE = "Case Documents Workspace"


def _serialize(document: CaseDocument) -> dict:
    try:
        entities = json.loads(document.extracted_entities or "[]")
    except json.JSONDecodeError:
        entities = []
    return {
        "id": document.id,
        "case_id": document.case_id,
        "name": document.original_filename,
        "type": document.file_type,
        "size_bytes": document.size_bytes,
        "uploaded_at": document.created_at.isoformat() if document.created_at else None,
        "status": document.status,
        "progress": document.progress,
        "pages": document.page_count,
        "extracted_text_available": bool(document.extracted_text),
        "extracted_entities": entities,
        "error": document.error_message,
        "ocr_used": document.ocr_used,
    }


def _case_for_lawyer(case_id: str, user: User, db: Session) -> LawyerCase:
    case = db.query(LawyerCase).filter(LawyerCase.id == case_id).first()
    if not case or case.lawyer_id != user.id:
        # Do not reveal another lawyer's case identifier.
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _validated_file_type(upload: UploadFile, data: bytes) -> tuple[str, str, str]:
    filename = Path(upload.filename or "document").name
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail=f"{filename}: unsupported file type")
    if not data:
        raise HTTPException(status_code=400, detail=f"{filename}: file is empty")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"{filename}: exceeds the 20 MB limit")

    if extension == "pdf" and not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail=f"{filename}: invalid PDF file")
    if extension == "docx":
        try:
            with zipfile.ZipFile(BytesIO(data)) as archive:
                if "[Content_Types].xml" not in archive.namelist():
                    raise ValueError
        except (ValueError, zipfile.BadZipFile):
            raise HTTPException(status_code=415, detail=f"{filename}: invalid DOCX file")
    if extension in {"jpg", "jpeg"} and not data.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=415, detail=f"{filename}: invalid JPEG file")
    if extension == "png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=415, detail=f"{filename}: invalid PNG file")

    return filename, extension, ALLOWED_TYPES[extension]


def _storage_required() -> None:
    if not mongo_available or fs is None:
        raise HTTPException(status_code=503, detail="Private document storage is unavailable. Start MongoDB and retry.")


@router.post("/cases/workspace")
def get_or_create_workspace(
    current_user: User = Depends(require_role("lawyer")), db: Session = Depends(get_db)
):
    case = (
        db.query(LawyerCase)
        .filter(LawyerCase.lawyer_id == current_user.id, LawyerCase.title == WORKSPACE_TITLE)
        .first()
    )
    if case is None:
        case = LawyerCase(lawyer_id=current_user.id, title=WORKSPACE_TITLE)
        db.add(case)
        db.commit()
        db.refresh(case)
    return {"id": case.id, "title": case.title, "created_at": case.created_at}


@router.get("/cases/{case_id}/documents")
def list_documents(
    case_id: str,
    current_user: User = Depends(require_role("lawyer")),
    db: Session = Depends(get_db),
):
    _case_for_lawyer(case_id, current_user, db)
    documents = (
        db.query(CaseDocument)
        .filter(CaseDocument.case_id == case_id)
        .order_by(CaseDocument.created_at.desc())
        .all()
    )
    return [_serialize(document) for document in documents]


@router.get("/cases/{case_id}/documents/metrics")
def document_metrics(
    case_id: str,
    current_user: User = Depends(require_role("lawyer")),
    db: Session = Depends(get_db),
):
    """Return document overview figures calculated from persisted records."""
    _case_for_lawyer(case_id, current_user, db)
    documents = db.query(CaseDocument).filter(CaseDocument.case_id == case_id).all()
    entity_count = 0
    for document in documents:
        try:
            entity_count += len(json.loads(document.extracted_entities or "[]"))
        except json.JSONDecodeError:
            continue
    return {
        "documents": len(documents),
        "pages": sum(document.page_count or 0 for document in documents),
        "extracted_entities": entity_count,
        "by_status": {state: sum(document.status == state for document in documents) for state in ("waiting", "uploading", "processing", "parsed", "failed")},
    }


@router.post("/cases/{case_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_documents(
    case_id: str,
    files: Annotated[list[UploadFile], File(...)],
    current_user: User = Depends(require_role("lawyer")),
    db: Session = Depends(get_db),
):
    _case_for_lawyer(case_id, current_user, db)
    _storage_required()
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one document")

    created: list[CaseDocument] = []
    for upload in files:
        data = await upload.read(MAX_FILE_SIZE + 1)
        filename, file_type, content_type = _validated_file_type(upload, data)
        document = CaseDocument(
            case_id=case_id,
            uploaded_by=current_user.id,
            original_filename=filename,
            file_type=file_type,
            content_type=content_type,
            size_bytes=len(data),
            status="uploading",
            progress=25,
        )
        db.add(document)
        db.flush()
        try:
            storage_ref = str(
                fs.put(
                    data,
                    filename=f"{document.id}_{filename}",
                    content_type=content_type,
                    metadata={
                        "case_id": case_id,
                        "document_id": document.id,
                        "sha256": hashlib.sha256(data).hexdigest(),
                    },
                )
            )
            document.storage_ref = storage_ref
            document.status = "processing"
            document.progress = 65
            db.commit()

            parsed = parse_case_document(data, file_type)
            document.extracted_text = parsed["text"]
            document.page_count = parsed["page_count"]
            document.ocr_used = parsed["ocr_used"]
            document.extracted_entities = json.dumps(parsed["entities"])
            document.status = "parsed"
            document.progress = 100
            document.error_message = None
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            document.status = "failed"
            document.progress = 100
            document.error_message = "The document could not be parsed. You can retry the upload."
        db.add(document)
        db.commit()
        db.refresh(document)
        created.append(document)
    return [_serialize(document) for document in created]


@router.delete("/cases/{case_id}/documents/{document_id}")
def delete_document(
    case_id: str,
    document_id: str,
    current_user: User = Depends(require_role("lawyer")),
    db: Session = Depends(get_db),
):
    _case_for_lawyer(case_id, current_user, db)
    document = (
        db.query(CaseDocument)
        .filter(CaseDocument.id == document_id, CaseDocument.case_id == case_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.storage_ref and mongo_available and fs is not None:
        try:
            fs.delete(ObjectId(document.storage_ref))
        except Exception:
            raise HTTPException(status_code=503, detail="Document storage is unavailable. Retry deletion later.")
    db.delete(document)
    db.commit()
    return {"status": "deleted", "document_id": document_id}


@router.post("/cases/{case_id}/documents/{document_id}/retry")
def retry_document_parse(
    case_id: str,
    document_id: str,
    current_user: User = Depends(require_role("lawyer")),
    db: Session = Depends(get_db),
):
    _case_for_lawyer(case_id, current_user, db)
    document = db.query(CaseDocument).filter(CaseDocument.id == document_id, CaseDocument.case_id == case_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    _storage_required()
    if not document.storage_ref:
        raise HTTPException(status_code=409, detail="This document was not stored and must be uploaded again.")
    try:
        data = fs.get(ObjectId(document.storage_ref)).read()
        document.status = "processing"
        document.progress = 65
        document.error_message = None
        db.commit()
        parsed = parse_case_document(data, document.file_type)
        document.extracted_text = parsed["text"]
        document.page_count = parsed["page_count"]
        document.ocr_used = parsed["ocr_used"]
        document.extracted_entities = json.dumps(parsed["entities"])
        document.status = "parsed"
        document.progress = 100
    except Exception:
        document.status = "failed"
        document.progress = 100
        document.error_message = "The document could not be parsed. You can retry the upload."
    db.add(document)
    db.commit()
    db.refresh(document)
    return _serialize(document)


@router.get("/cases/{case_id}/documents/{document_id}/download")
def download_document(
    case_id: str,
    document_id: str,
    current_user: User = Depends(require_role("lawyer")),
    db: Session = Depends(get_db),
):
    _case_for_lawyer(case_id, current_user, db)
    document = db.query(CaseDocument).filter(CaseDocument.id == document_id, CaseDocument.case_id == case_id).first()
    if not document or not document.storage_ref:
        raise HTTPException(status_code=404, detail="Document not found")
    _storage_required()
    try:
        stored = fs.get(ObjectId(document.storage_ref))
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")
    return StreamingResponse(
        stored,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{document.original_filename}"'},
    )


@router.post("/cases/{case_id}/documents/analyze")
def begin_analysis(
    case_id: str,
    current_user: User = Depends(require_role("lawyer")),
    db: Session = Depends(get_db),
):
    _case_for_lawyer(case_id, current_user, db)
    # Compatibility route retained for earlier frontend clients.  Delegate to
    # the canonical case-analysis endpoint rather than reporting a stale 501.
    from app.routers.lawyer_workflow import analyze
    return analyze(case_id=case_id, current_user=current_user, db=db)
