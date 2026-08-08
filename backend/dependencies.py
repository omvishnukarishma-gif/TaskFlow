"""
dependencies.py — Reusable FastAPI dependency for database sessions.

Usage in route handlers:
    def my_route(db: Session = Depends(get_db)):
        ...

The generator pattern ensures the session is always closed after the request,
even if an exception is raised.
"""

from typing import Generator

from sqlalchemy.orm import Session

from backend.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and guarantee it is closed afterwards."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
