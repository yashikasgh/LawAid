from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/message")
def send_message():
    return {"status": "not_implemented", "response": "This feature is coming soon."}

@router.get("/history/{session_id}")
def get_history(session_id: str):
    return {"session_id": session_id, "messages": []}