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
    except Exception:
        # Fallback keyword match in standard BNS offences
        lowered = user_msg.lower()
        if "cheat" in lowered or "fraud" in lowered:
            retrieved_sections.append("Section 318: Cheating (Bailable)")
        elif "theft" in lowered or "steal" in lowered:
            retrieved_sections.append("Section 303: Theft (Non-bailable)")
        elif "threat" in lowered or "intimidat" in lowered:
            retrieved_sections.append("Section 351: Criminal Intimidation (Bailable)")
        elif "assault" in lowered or "hurt" in lowered:
            retrieved_sections.append("Section 115: Voluntarily Causing Hurt")

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
        except Exception:
            bot_reply = ""

    # Rule-based fallback if Groq is unavailable
    if not bot_reply:
        sec_text = (
            f"Applicable BNS provisions identified:\n• " + "\n• ".join(retrieved_sections)
            if retrieved_sections
            else "Relevant provisions: General provisions under the Bharatiya Nyaya Sanhita (BNS), 2023."
        )
        bot_reply = (
            f"Thank you for reaching out. Based on your inquiry, here is the relevant legal guidance:\n\n"
            f"{sec_text}\n\n"
            f"Key Citizen Rights:\n"
            f"1. You have the right to file an FIR at any police station (Zero FIR provision under Section 173(1) BNSS).\n"
            f"2. You are entitled to a free copy of the FIR immediately.\n"
            f"3. For emergency police assistance, dial 112. For free government legal assistance, call NALSA at 15100.\n\n"
            f"Disclaimer: This information is for educational guidance and does not replace consultation with a licensed advocate."
        )

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