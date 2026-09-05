from fastapi import APIRouter

router = APIRouter(prefix="/police", tags=["police"])

@router.post("/transcribe")
def transcribe_statement():
    return {"status": "not_implemented", "transcript": ""}

@router.post("/validate-fir")
def validate_fir():
    return {"status": "not_implemented", "sections": []}

@router.post("/approve-fir")
def approve_fir():
    return {"status": "not_implemented", "fir_id": "STUB-001"}