from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.core.mongo import mongo_available, mongo_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
import datetime
from bson import ObjectId

router = APIRouter(prefix="/fir/drafts", tags=["fir_drafts"])

@router.post("")
def save_draft(body: Dict[str, Any], current_user: User = Depends(require_role("police"))):
    if not mongo_available or mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable, cannot save drafts.")
    
    draft_data = body
    draft_id = draft_data.get("_id") or draft_data.get("draft_id")
    
    # Clean up IDs before saving
    if "_id" in draft_data:
        del draft_data["_id"]
    if "draft_id" in draft_data:
        del draft_data["draft_id"]
        
    draft_data["officer_id"] = current_user.id
    draft_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    collection = mongo_db["fir_drafts"]
    
    if draft_id and ObjectId.is_valid(draft_id):
        # Update existing
        draft_data.setdefault("created_at", draft_data["updated_at"])
        collection.update_one({"_id": ObjectId(draft_id)}, {"$set": draft_data})
        return {"draft_id": str(draft_id), "status": "updated"}
    else:
        # Create new
        draft_data["created_at"] = draft_data["updated_at"]
        result = collection.insert_one(draft_data)
        return {"draft_id": str(result.inserted_id), "status": "created"}

@router.get("")
def get_drafts(current_user: User = Depends(require_role("police"))):
    if not mongo_available or mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable, cannot retrieve drafts.")
        
    collection = mongo_db["fir_drafts"]
    drafts = list(collection.find({"officer_id": current_user.id}).sort("updated_at", -1))
    
    for d in drafts:
        d["draft_id"] = str(d["_id"])
        del d["_id"]
        
    return drafts

@router.get("/{draft_id}")
def get_draft(draft_id: str, current_user: User = Depends(require_role("police"))):
    if not mongo_available or mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable.")
        
    if not ObjectId.is_valid(draft_id):
        raise HTTPException(status_code=400, detail="Invalid draft ID")
        
    collection = mongo_db["fir_drafts"]
    draft = collection.find_one({"_id": ObjectId(draft_id)})
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
        
    if draft.get("officer_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    draft["draft_id"] = str(draft["_id"])
    del draft["_id"]
    
    return draft

@router.delete("/{draft_id}")
def delete_draft(draft_id: str, current_user: User = Depends(require_role("police"))):
    if not mongo_available or mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable.")
        
    if not ObjectId.is_valid(draft_id):
        raise HTTPException(status_code=400, detail="Invalid draft ID")
        
    collection = mongo_db["fir_drafts"]
    result = collection.delete_one({"_id": ObjectId(draft_id), "officer_id": current_user.id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Draft not found or not authorized")
        
    return {"status": "deleted"}

