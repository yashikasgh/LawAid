from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.routers import auth, fir, police, chat
from app.middleware.audit_log import audit_log_middleware

app = FastAPI(title="LawAid Backend")

app.middleware("http")(audit_log_middleware)
app.include_router(auth.router)
app.include_router(fir.router)
app.include_router(police.router)
app.include_router(chat.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "LawAid backend"}

@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}

from app.core.deps import get_current_user

@app.get("/auth/me")
def read_current_user(current_user = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}