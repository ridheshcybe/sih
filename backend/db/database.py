from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import DATABASE_URL

DB_PATH = Path(DATABASE_URL.replace("sqlite:///", "", 1)) if DATABASE_URL.startswith("sqlite:///") else None
if DB_PATH is not None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Import models so Base.metadata includes the ORM tables.
import backend.db.models  # noqa: F401


def create_all_tables() -> None:
    """Create database tables defined by ORM models."""
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    create_all_tables()
