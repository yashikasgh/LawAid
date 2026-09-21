from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.core.mongo import mongo_available, mongo_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
import datetime
from bson import ObjectId

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.fir_draft import FIRDraft
import json

router = APIRouter(prefix="/fir/drafts", tags=["fir_drafts"])

@router.post("")
def save_draft(
    body: Dict[str, Any],
    current_user: User = Depends(require_role("police")),
    db: Session = Depends(get_db),
):
    draft_data = dict(body)
    draft_id = draft_data.get("_id") or draft_data.get("draft_id")
    
    # Clean up IDs before saving
    if "_id" in draft_data:
        del draft_data["_id"]
    if "draft_id" in draft_data:
        del draft_data["draft_id"]
        
    draft_data["officer_id"] = current_user.id
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    draft_data["updated_at"] = now_iso
    
    if mongo_available and mongo_db is not None:
        collection = mongo_db["fir_drafts"]
        if draft_id and ObjectId.is_valid(draft_id):
            draft_data.setdefault("created_at", now_iso)
            collection.update_one({"_id": ObjectId(draft_id)}, {"$set": draft_data})
            return {"draft_id": str(draft_id), "status": "updated"}
        else:
            draft_data["created_at"] = now_iso
            result = collection.insert_one(draft_data)
            return {"draft_id": str(result.inserted_id), "status": "created"}
    else:
        # Persistent SQLite storage when MongoDB is not running
        if not draft_id:
            draft_id = str(ObjectId())
        draft_data["draft_id"] = draft_id
        draft_data.setdefault("created_at", now_iso)

        json_payload = json.dumps(draft_data)
        existing = db.query(FIRDraft).filter(FIRDraft.draft_id == str(draft_id)).first()
        if existing:
            existing.data = json_payload
            db.commit()
            return {"draft_id": str(draft_id), "status": "updated"}
        else:
            record = FIRDraft(draft_id=str(draft_id), officer_id=current_user.id, data=json_payload)
            db.add(record)
            db.commit()
            return {"draft_id": str(draft_id), "status": "created"}

@router.get("")
def get_drafts(
    current_user: User = Depends(require_role("police")),
    db: Session = Depends(get_db),
):
    if mongo_available and mongo_db is not None:
        collection = mongo_db["fir_drafts"]
        drafts = list(collection.find({"officer_id": current_user.id}).sort("updated_at", -1))
        for d in drafts:
            d["draft_id"] = str(d["_id"])
            if "_id" in d:
                del d["_id"]
        return drafts
    else:
        # Persistent SQLite query for current officer
        records = db.query(FIRDraft).filter(FIRDraft.officer_id == current_user.id).order_by(FIRDraft.updated_at.desc()).all()
        results = []
        for r in records:
            try:
                parsed = json.loads(r.data)
                parsed["draft_id"] = r.draft_id
                parsed["officer_id"] = r.officer_id
                if r.updated_at:
                    parsed["updated_at"] = r.updated_at.isoformat()
                results.append(parsed)
            except Exception:
                pass
        return results

@router.get("/{draft_id}")
def get_draft(
    draft_id: str,
    current_user: User = Depends(require_role("police")),
    db: Session = Depends(get_db),
):
    if mongo_available and mongo_db is not None:
        if not ObjectId.is_valid(draft_id):
            raise HTTPException(status_code=400, detail="Invalid draft ID")
            
        collection = mongo_db["fir_drafts"]
        draft = collection.find_one({"_id": ObjectId(draft_id)})
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
            
        if draft.get("officer_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        draft["draft_id"] = str(draft["_id"])
        if "_id" in draft:
            del draft["_id"]
        return draft
    else:
        record = db.query(FIRDraft).filter(FIRDraft.draft_id == str(draft_id)).first()
        if not record or record.officer_id != current_user.id:
            raise HTTPException(status_code=404, detail="Draft not found or not authorized")
        try:
            parsed = json.loads(record.data)
            parsed["draft_id"] = record.draft_id
            parsed["officer_id"] = record.officer_id
            if record.updated_at:
                parsed["updated_at"] = record.updated_at.isoformat()
            return parsed
        except Exception:
            raise HTTPException(status_code=500, detail="Corrupted draft record")

@router.delete("/{draft_id}")
def delete_draft(
    draft_id: str,
    current_user: User = Depends(require_role("police")),
    db: Session = Depends(get_db),
):
    if mongo_available and mongo_db is not None:
        if not ObjectId.is_valid(draft_id):
            raise HTTPException(status_code=400, detail="Invalid draft ID")
            
        collection = mongo_db["fir_drafts"]
        result = collection.delete_one({"_id": ObjectId(draft_id), "officer_id": current_user.id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Draft not found or not authorized")
            
        return {"status": "deleted"}
    else:
        record = db.query(FIRDraft).filter(FIRDraft.draft_id == str(draft_id)).first()
        if not record or record.officer_id != current_user.id:
            raise HTTPException(status_code=404, detail="Draft not found or not authorized")
        db.delete(record)
        db.commit()
        return {"status": "deleted"}


