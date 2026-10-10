import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class CaseDocument(Base):
    __tablename__ = "case_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("lawyer_cases.id"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    content_type = Column(String(120), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_ref = Column(String(64), nullable=True, unique=True)
    status = Column(String(20), nullable=False, default="waiting")
    progress = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=True)
    extracted_text = Column(Text, nullable=True)
    extracted_entities = Column(Text, nullable=True)
    extraction_details = Column(Text, nullable=True)
    structured_extraction = Column(Text, nullable=True)
    error_message = Column(String(500), nullable=True)
    ocr_used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
