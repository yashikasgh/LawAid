from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class FIRRegistry(Base):
    __tablename__ = "fir_registry"

    id = Column(Integer, primary_key=True, index=True)
    fir_id = Column(String, unique=True, nullable=False, index=True)
    sha256_hash = Column(String, nullable=False)
    officer_id = Column(Integer, nullable=False)
    station_code = Column(String, nullable=False)
    status = Column(String, default="registered")
    created_at = Column(DateTime(timezone=True), server_default=func.now())