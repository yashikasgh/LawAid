import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

Base = declarative_base()

def _init_engine():
    db_url = settings.DATABASE_URL
    try:
        # Check if PostgreSQL is actively listening
        test_engine = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2}
        )
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[DATABASE] Successfully connected to PostgreSQL.")
        return test_engine
    except Exception as err:
        sqlite_path = settings.REPOSITORY_ROOT / "backend" / "lawaid.db"
        sqlite_url = f"sqlite:///{sqlite_path}"
        print(f"[DATABASE WARNING] PostgreSQL unavailable ({err}). Using local SQLite: {sqlite_url}")
        sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        
        # Auto-create all tables in SQLite fallback so app runs out of the box
        try:
            from app.models.user import User  # noqa: F401
            from app.models.session import SessionModel  # noqa: F401
            from app.models.audit_log import AuditLog  # noqa: F401
            from app.models.fir_registry import FIRRegistry  # noqa: F401
            Base.metadata.create_all(bind=sqlite_engine)
        except Exception:
            pass
            
        return sqlite_engine

engine = _init_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()