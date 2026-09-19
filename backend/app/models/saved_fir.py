from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base

class SavedFIR(Base):
    __tablename__ = "saved_firs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    gridfs_file_id = Column(String, nullable=True)
    extracted_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=False)
    charges = Column(Text, nullable=True)             # JSON string of charges
    reference_provisions = Column(Text, nullable=True) # JSON string of reference provisions
    rights = Column(Text, nullable=True)               # JSON string of rights
    next_steps = Column(Text, nullable=True)           # JSON string of next steps
    disclaimer = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
