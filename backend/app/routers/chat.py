import os
import uuid
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import datetime
from bson import ObjectId
from app.core.mongo import mongo_available, mongo_db
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])

# Fallback in-memory session store if MongoDB is unavailable
_SESSIONS: Dict[str, Any] = {}

class ChatMessageRequest(BaseModel):
    session_id: str = None
    message: str

@router.post("/session")
def create_session(current_user: User = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        collection.insert_one({
            "_id": session_id,
            "user_id": current_user.id,
            "messages": [],
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
    else:
        _SESSIONS[session_id] = {
            "user_id": current_user.id,
            "messages": [],
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
    return {"session_id": session_id, "status": "created"}

@router.post("/message")
def send_message(body: ChatMessageRequest, current_user: User = Depends(get_current_user)):
    user_msg = body.message.strip() if body.message else ""
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = body.session_id or str(uuid.uuid4())
    
    # 1. Store user message
    user_msg_obj = {
        "role": "user", 
        "content": user_msg, 
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        # Create session if it doesnt exist
        if not collection.find_one({"_id": session_id}):
             collection.insert_one({
                "_id": session_id,
                "user_id": current_user.id,
                "messages": [],
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
        collection.update_one({"_id": session_id}, {"$push": {"messages": user_msg_obj}, "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}})
    else:
        if session_id not in _SESSIONS:
            _SESSIONS[session_id] = {"user_id": current_user.id, "messages": [], "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        _SESSIONS[session_id]["messages"].append(user_msg_obj)

    # 2. Call AI
    try:
        from ai.rag.pipeline import run_chat_pipeline
        result = run_chat_pipeline(raw_message=user_msg)
    except Exception as e:
        # Graceful failure if AI blocked
        result = {"reply": "AI RAG pipeline is currently unavailable. " + str(e), "sections": [], "disclaimer": ""}

    bot_reply = result.get("reply", "")
    retrieved_sections = result.get("sections", [])
    disclaimer = result.get("disclaimer", "")

    # 3. Store assistant message
    bot_msg_obj = {
        "role": "assistant", 
        "content": bot_reply,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        collection.update_one({"_id": session_id}, {"$push": {"messages": bot_msg_obj}, "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}})
    else:
        _SESSIONS[session_id]["messages"].append(bot_msg_obj)

    return {
        "status": "ok",
        "session_id": session_id,
        "reply": bot_reply,
        "sections": retrieved_sections,
        "disclaimer": disclaimer
    }

@router.get("/sessions")
def get_sessions(current_user: User = Depends(get_current_user)):
    sessions = []
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        cursor = collection.find({"user_id": current_user.id}).sort("updated_at", -1)
        for doc in cursor:
            # Generate a preview from the first message
            preview = "Empty chat"
            if doc.get("messages") and len(doc["messages"]) > 0:
                preview = doc["messages"][0]["content"][:50] + "..."
            sessions.append({
                "session_id": doc["_id"],
                "preview": preview,
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at")
            })
    else:
        for sid, sdata in _SESSIONS.items():
            if sdata.get("user_id") == current_user.id:
                preview = "Empty chat"
                if sdata.get("messages") and len(sdata["messages"]) > 0:
                    preview = sdata["messages"][0]["content"][:50] + "..."
                sessions.append({
                    "session_id": sid,
                    "preview": preview,
                    "created_at": sdata.get("created_at")
                })
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
    return sessions

@router.get("/history/{session_id}")
def get_history(session_id: str, current_user: User = Depends(get_current_user)):
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        session = collection.find_one({"_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if session.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this chat")
        return {"session_id": session_id, "messages": session.get("messages", [])}
    else:
        session = _SESSIONS.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if session.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return {"session_id": session_id, "messages": session.get("messages", [])}

