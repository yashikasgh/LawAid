import os
import uuid
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session store: session_id -> list of {"role": "user"|"assistant", "content": str}
_SESSIONS: Dict[str, List[Dict[str, str]]] = {}

class ChatMessageRequest(BaseModel):
    session_id: str = None
    message: str


@router.post("/message")
def send_message(body: ChatMessageRequest):
    """
    Legal AI Assistant grounded in the Bharatiya Nyaya Sanhita (BNS) 2023.
    Passes user question through the shared LawAid RAG legal pipeline and returns
    a grounded conversational response, applicable section titles, and legal disclaimer.
    """
    user_msg = body.message.strip() if body.message else ""
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = body.session_id or str(uuid.uuid4())
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = []

    # Record user message
    _SESSIONS[session_id].append({"role": "user", "content": user_msg})

    try:
        from ai.rag.pipeline import run_chat_pipeline
        result = run_chat_pipeline(raw_message=user_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Legal Chat RAG Pipeline Error: {str(e)}")

    bot_reply = result.get("reply", "")
    retrieved_sections = result.get("sections", [])
    disclaimer = result.get("disclaimer", "")

    # Record assistant reply
    _SESSIONS[session_id].append({"role": "assistant", "content": bot_reply})

    return {
        "status": "ok",
        "session_id": session_id,
        "reply": bot_reply,
        "sections": retrieved_sections,
        "disclaimer": disclaimer
    }


@router.get("/history/{session_id}")
def get_history(session_id: str):
    messages = _SESSIONS.get(session_id, [])
    return {"session_id": session_id, "messages": messages}