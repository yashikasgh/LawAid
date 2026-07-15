from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.mongo import fs

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

@router.get("/{fir_id}")
def get_fir(fir_id: str):
    return {"fir_id": fir_id, "status": "not_implemented"}

@router.post("/verify")
def verify_fir():
    return {"status": "not_implemented", "match": False}