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
    Accepts user question, retrieves relevant legal provisions, and responds
    with plain-language guidance, applicable sections, and disclaimer.
    """
    user_msg = body.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = body.session_id or str(uuid.uuid4())
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = []

    # Record user message
    _SESSIONS[session_id].append({"role": "user", "content": user_msg})

    # Retrieve matching BNS context if available
    retrieved_sections = []
    try:
        from ai.rag.retrieval.retrieve_bns import retrieve
        matches = retrieve(user_msg, top_k=3)
        for m in matches:
            dist = float(m.get("distance", 1.0))
            if dist < 0.75:
                retrieved_sections.append(f"Section {m.get('section')}: {m.get('title')}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BNS Retrieval Error: {str(e)}")

    # Generate response via Groq if configured
    groq_key = os.environ.get("GROQ_API_KEY")
    bot_reply = ""
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            context_str = "\n".join(retrieved_sections) if retrieved_sections else "General Indian Criminal Law (BNS 2023)."
            prompt = (
                f"You are LawAid's compassionate Legal AI Assistant specializing in Indian law (BNS 2023 & BNSS 2023).\n"
                f"Context provisions:\n{context_str}\n\n"
                f"User Question: {user_msg}\n\n"
                f"Instructions: Provide a clear, empathetic explanation in simple language. "
                f"Mention the specific relevant section numbers, whether offences are bailable/cognizable, and citizen rights. "
                f"End with a standard brief reminder that this is for educational purposes and not formal legal representation."
            )
            completion = client.chat.completions.create(
                model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600,
            )
            bot_reply = completion.choices[0].message.content
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Groq LLM Error: {str(e)}")
    else:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured in environment.")

    # Record assistant reply
    _SESSIONS[session_id].append({"role": "assistant", "content": bot_reply})

    return {
        "status": "ok",
        "session_id": session_id,
        "reply": bot_reply,
        "sections": retrieved_sections,
    }


@router.get("/history/{session_id}")
def get_history(session_id: str):
    messages = _SESSIONS.get(session_id, [])
    return {"session_id": session_id, "messages": messages}