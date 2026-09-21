from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base

class FIRDraft(Base):
    __tablename__ = "fir_drafts"

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(String, unique=True, index=True, nullable=False)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    data = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
