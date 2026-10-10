import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class CaseAnalysis(Base):
    __tablename__ = "case_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("lawyer_cases.id"), nullable=False, unique=True, index=True)
    payload = Column(Text, nullable=False, default="{}")
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CaseTimelineEvent(Base):
    __tablename__ = "case_timeline_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("lawyer_cases.id"), nullable=False, index=True)
    source_document_id = Column(String(36), ForeignKey("case_documents.id"), nullable=True)
    event_date = Column(String(10), nullable=False)
    event_time = Column(String(20), nullable=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    event_type = Column(String(40), nullable=False, default="Incident")
    related_bns_sections = Column(Text, nullable=False, default="[]")
    source_reference = Column(Text, nullable=True)
    confidence = Column(String(20), nullable=False, default="needs_review")
    is_edited = Column(String(5), nullable=False, default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CaseSummary(Base):
    __tablename__ = "case_summaries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("lawyer_cases.id"), nullable=False, unique=True, index=True)
    executive_summary = Column(Text, nullable=False, default="")
    current_stage = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
