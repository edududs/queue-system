from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Detect invalid connections (e.g., "MySQL has gone away")
    pool_recycle=7200,  # Recycle connections to avoid timeouts
    echo=settings.DEBUG,  # Enable SQL logging in development
    future=True,  # Ensure SQLAlchemy 2.x style behavior
)

# Session factory (without autocommit/autoflush)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]
