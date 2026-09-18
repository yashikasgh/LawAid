import os
import json
import uuid
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import datetime
from bson import ObjectId
from sqlalchemy.orm import Session as DBSession

from app.core.mongo import mongo_available, mongo_db
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.chat import ChatSessionModel

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory fallback if both Mongo and SQL fail
_SESSIONS: Dict[str, Any] = {}

class ChatMessageRequest(BaseModel):
    session_id: str = None
    message: str

@router.post("/session")
def create_session(current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
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
        chat_sess = ChatSessionModel(
            id=session_id,
            user_id=current_user.id,
            messages_json=json.dumps([])
        )
        db.add(chat_sess)
        db.commit()
        
    return {"session_id": session_id, "status": "created"}

@router.post("/message")
def send_message(body: ChatMessageRequest, current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
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
    
    messages_list = []
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        sess_doc = collection.find_one({"_id": session_id})
        if not sess_doc:
            collection.insert_one({
                "_id": session_id,
                "user_id": current_user.id,
                "messages": [user_msg_obj],
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            messages_list = [user_msg_obj]
        else:
            collection.update_one(
                {"_id": session_id},
                {"$push": {"messages": user_msg_obj}, "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
            )
            messages_list = sess_doc.get("messages", []) + [user_msg_obj]
    else:
        chat_sess = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
        if not chat_sess:
            chat_sess = ChatSessionModel(
                id=session_id,
                user_id=current_user.id,
                messages_json=json.dumps([user_msg_obj])
            )
            db.add(chat_sess)
            db.commit()
            messages_list = [user_msg_obj]
        else:
            try:
                curr_msgs = json.loads(chat_sess.messages_json or "[]")
            except Exception:
                curr_msgs = []
            curr_msgs.append(user_msg_obj)
            chat_sess.messages_json = json.dumps(curr_msgs)
            db.commit()
            messages_list = curr_msgs

    # 2. Extract recent conversation history (excluding current user message just added)
    past_msgs = messages_list[:-1] if len(messages_list) > 1 else []
    history = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in past_msgs[-6:]]

    # 3. Call AI with history context
    try:
        from ai.rag.pipeline import run_chat_pipeline
        result = run_chat_pipeline(raw_message=user_msg, history=history)
    except Exception as e:
        result = {"reply": "AI RAG pipeline is currently unavailable. " + str(e), "sections": [], "disclaimer": ""}

    bot_reply = result.get("reply", "")
    retrieved_sections = result.get("sections", [])
    disclaimer = result.get("disclaimer", "")

    # 4. Store assistant message
    bot_msg_obj = {
        "role": "assistant", 
        "content": bot_reply,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        collection.update_one({"_id": session_id}, {"$push": {"messages": bot_msg_obj}, "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}})
    else:
        chat_sess = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
        if chat_sess:
            try:
                curr_msgs = json.loads(chat_sess.messages_json or "[]")
            except Exception:
                curr_msgs = []
            curr_msgs.append(bot_msg_obj)
            chat_sess.messages_json = json.dumps(curr_msgs)
            db.commit()

    return {
        "status": "ok",
        "session_id": session_id,
        "reply": bot_reply,
        "sections": retrieved_sections,
        "disclaimer": disclaimer
    }

@router.get("/sessions")
def get_sessions(current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    sessions = []
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        cursor = collection.find({"user_id": current_user.id}).sort("updated_at", -1)
        for doc in cursor:
            messages = doc.get("messages", [])
            user_messages = [m for m in messages if isinstance(m, dict) and m.get("role") == "user" and str(m.get("content", "")).strip()]
            if not user_messages:
                continue
            first_user_content = user_messages[0]["content"].strip()
            preview = first_user_content[:50]
            if len(first_user_content) > 50:
                preview += "..."
            sessions.append({
                "session_id": doc["_id"],
                "preview": preview,
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at")
            })
    else:
        db_sessions = db.query(ChatSessionModel).filter(ChatSessionModel.user_id == current_user.id).order_by(ChatSessionModel.updated_at.desc()).all()
        for sess in db_sessions:
            try:
                messages = json.loads(sess.messages_json or "[]")
            except Exception:
                messages = []
            user_messages = [m for m in messages if isinstance(m, dict) and m.get("role") == "user" and str(m.get("content", "")).strip()]
            if not user_messages:
                continue
            first_user_content = user_messages[0]["content"].strip()
            preview = first_user_content[:50]
            if len(first_user_content) > 50:
                preview += "..."
            sessions.append({
                "session_id": sess.id,
                "preview": preview,
                "created_at": sess.created_at.isoformat() if sess.created_at else None,
                "updated_at": sess.updated_at.isoformat() if sess.updated_at else None
            })
        
    return sessions

@router.delete("/session/{session_id}")
@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        session = collection.find_one({"_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if session.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this chat")
        collection.delete_one({"_id": session_id})
    else:
        sess = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
        if not sess:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if sess.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        db.delete(sess)
        db.commit()

    return {"status": "deleted", "session_id": session_id}


@router.get("/history/{session_id}")
def get_history(session_id: str, current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if mongo_available and mongo_db is not None:
        collection = mongo_db["chat_sessions"]
        session = collection.find_one({"_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if session.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this chat")
        return {"session_id": session_id, "messages": session.get("messages", [])}
    else:
        sess = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
        if not sess:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if sess.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        try:
            messages = json.loads(sess.messages_json or "[]")
        except Exception:
            messages = []
        return {"session_id": session_id, "messages": messages}
