from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.models.complaint import Complaint
from pydantic import BaseModel
import json

router = APIRouter(prefix="/complaints", tags=["complaints"])

class ComplaintCreate(BaseModel):
    complaint_text: str
    detected_sections: list[str] = []
    language: str = "en"
    duplicate_status: str = ""

@router.post("")
def create_complaint(body: ComplaintCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("citizen", "police"))):
    new_complaint = Complaint(
        user_id=current_user.id,
        complaint_text=body.complaint_text,
        detected_sections=json.dumps(body.detected_sections),
        language=body.language,
        duplicate_status=body.duplicate_status,
        status="PENDING"
    )
    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)
    return new_complaint

@router.get("/my")
def get_my_complaints(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    complaints = db.query(Complaint).filter(Complaint.user_id == current_user.id).order_by(Complaint.created_at.desc()).all()
    # parse detected sections json
    result = []
    for c in complaints:
        c_dict = {
            "id": c.id,
            "complaint_text": c.complaint_text,
            "status": c.status,
            "language": c.language,
            "duplicate_status": c.duplicate_status,
            "created_at": c.created_at,
            "updated_at": c.updated_at
        }
        try:
            c_dict["detected_sections"] = json.loads(c.detected_sections) if c.detected_sections else []
        except:
            c_dict["detected_sections"] = []
        result.append(c_dict)
    return result

@router.get("/{complaint_id}")
def get_complaint(complaint_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    if c.user_id != current_user.id and current_user.role != "police":
        raise HTTPException(status_code=403, detail="Not authorized to view this complaint")
        
    c_dict = {
        "id": c.id,
        "complaint_text": c.complaint_text,
        "status": c.status,
        "language": c.language,
        "duplicate_status": c.duplicate_status,
        "created_at": c.created_at,
        "updated_at": c.updated_at
    }
    try:
        c_dict["detected_sections"] = json.loads(c.detected_sections) if c.detected_sections else []
    except:
        c_dict["detected_sections"] = []
        
    return c_dict

