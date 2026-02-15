# app/database.py - Database Configuration
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Database URL loaded from .env via app/config.py
DATABASE_URL = settings.DATABASE_URL

def _create_engine(url: str):
    if str(url).startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url)


# Create engine (with local fallback when postgres driver is unavailable)
try:
    engine = _create_engine(DATABASE_URL)
except ModuleNotFoundError as exc:  # pragma: no cover - environment fallback
    if "psycopg2" not in str(exc):
        raise
    fallback_url = os.getenv("FALLBACK_DATABASE_URL", "sqlite:///./skillswap.db")
    engine = _create_engine(fallback_url)

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
