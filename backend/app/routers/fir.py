from fastapi import APIRouter

router = APIRouter(prefix="/fir", tags=["fir"])

@router.post("/generate")
def generate_fir():
    return {"fir_id": "STUB-001", "status": "not_implemented"}

@router.post("/upload")
def upload_fir():
    return {"status": "not_implemented", "message": "FIR upload not yet implemented"}

@router.get("/{fir_id}")
def get_fir(fir_id: str):
    return {"fir_id": fir_id, "status": "not_implemented"}

@router.post("/verify")
def verify_fir():
    return {"status": "not_implemented", "match": False}