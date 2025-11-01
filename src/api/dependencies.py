"""
Dependency injection for FastAPI routes.

Provides database sessions and other dependencies for API endpoints.
"""

import logging
from typing import Generator

from sqlalchemy.orm import Session

from src.db.config import get_session

# Configure logging
logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    """
    Get a database session for dependency injection.

    Yields:
        SQLAlchemy Session instance

    Example:
        @app.get("/matches")
        def get_matches(db: Session = Depends(get_db)):
            return db.query(Match).all()
    """
    db = get_session()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
