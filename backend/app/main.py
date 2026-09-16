from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.routers import auth, fir, police, chat, complaints, fir_drafts
from app.middleware.audit_log import audit_log_middleware

app = FastAPI(title="LawAid Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.middleware("http")(audit_log_middleware)
app.include_router(auth.router)
app.include_router(fir.router)
app.include_router(police.router)
app.include_router(chat.router)
app.include_router(complaints.router)
app.include_router(fir_drafts.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "LawAid backend"}

@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}

@app.get("/health/mongo")
def health_check_mongo():
    """Reports MongoDB/GridFS availability."""
    from app.core.mongo import mongo_available
    if mongo_available:
        return {"status": "ok", "mongodb": "connected"}
    return {"status": "unavailable", "mongodb": "disconnected",
            "detail": "MongoDB is not running. File storage endpoints (upload, download) are disabled."}

from app.core.deps import get_current_user

@app.get("/auth/me")
def read_current_user(current_user = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}