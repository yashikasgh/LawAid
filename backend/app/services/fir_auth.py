import uuid
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.fir_registry import FIRRegistry

def generate_fir_id(state: str, station_code: str) -> str:
    year = datetime.now().year
    serial = uuid.uuid4().hex[:5].upper()
    return f"FIR/{state}/{year}/{station_code}/{serial}"

def hash_document(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def register_fir(
    db: Session,
    file_bytes: bytes,
    officer_id: int,
    station_code: str,
    state: str = "MH",
) -> FIRRegistry:
    fir_id = generate_fir_id(state, station_code)
    sha256_hash = hash_document(file_bytes)

    fir_record = FIRRegistry(
        fir_id=fir_id,
        sha256_hash=sha256_hash,
        officer_id=officer_id,
        station_code=station_code,
        status="registered",
    )
    db.add(fir_record)
    db.commit()
    db.refresh(fir_record)
    return fir_record

def verify_fir(db: Session, fir_id: str, file_bytes: bytes) -> dict:
    record = db.query(FIRRegistry).filter(FIRRegistry.fir_id == fir_id).first()
    if not record:
        return {"match": False, "reason": "FIR ID not found"}

    current_hash = hash_document(file_bytes)
    match = current_hash == record.sha256_hash
    return {
        "match": match,
        "fir_id": fir_id,
        "stored_hash": record.sha256_hash,
        "computed_hash": current_hash,
    }