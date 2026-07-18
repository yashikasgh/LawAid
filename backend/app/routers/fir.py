from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.core.mongo import fs
from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.fir_auth import register_fir, verify_fir
from app.models.user import User

router = APIRouter(prefix="/fir", tags=["fir"])

@router.post("/generate")
def generate_fir():
    return {"fir_id": "STUB-001", "status": "not_implemented"}

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

@router.get("/{fir_id}")
def get_fir(fir_id: str):
    return {"fir_id": fir_id, "status": "not_implemented"}

@router.post("/verify")
async def verify_fir_route(
    fir_id: str = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    result = verify_fir(db=db, fir_id=fir_id, file_bytes=contents)
    return result

@router.get("/bns/search")
def search_bns(query: str = Query(..., min_length=3)):
    mock_results = [
        {"section": "318", "title": "Cheating", "similarity": 0.81},
        {"section": "351", "title": "Criminal Intimidation", "similarity": 0.68},
    ]
    top_result = mock_results[0]
    if top_result["similarity"] < 0.72:
        return {"status": "insufficient_information", "results": []}
    return {"status": "ok", "results": mock_results}