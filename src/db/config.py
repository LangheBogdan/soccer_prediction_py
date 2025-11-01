"""
Database configuration and connection setup.

This module handles:
- Database connection string creation
- SQLAlchemy engine and session factory
- Database initialization
"""

import os
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_database_url() -> str:
    """
    Construct database URL from environment variables.

    Supports both PostgreSQL (production) and SQLite (testing/development).

    Environment variables:
    - DATABASE_URL: Full database URL (overrides other settings)
    - DB_ENGINE: 'postgresql' or 'sqlite' (default: 'postgresql')
    - DB_HOST: Database host (PostgreSQL)
    - DB_PORT: Database port (PostgreSQL, default: 5432)
    - DB_NAME: Database name
    - DB_USER: Database user (PostgreSQL)
    - DB_PASSWORD: Database password (PostgreSQL)

    Returns:
        str: SQLAlchemy database URL
    """
    # Check for explicit DATABASE_URL first
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    db_engine = os.getenv("DB_ENGINE", "postgresql")

    if db_engine == "sqlite":
        db_path = os.getenv("DB_PATH", "data/soccer_prediction.db")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        return f"sqlite:///{db_path}"

    elif db_engine == "postgresql":
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "soccer_prediction")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "postgres")

        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    else:
        raise ValueError(f"Unsupported database engine: {db_engine}")


# Create engine
def create_db_engine(url: Optional[str] = None, echo: bool = False) -> Engine:
    """
    Create SQLAlchemy engine with proper configuration.

    Args:
        url: Database URL. If None, uses get_database_url()
        echo: Whether to echo SQL statements (default: False)

    Returns:
        SQLAlchemy Engine instance
    """
    if url is None:
        url = get_database_url()

    engine = create_engine(
        url,
        echo=echo,
        pool_pre_ping=True,  # Verify connection is alive before using
        pool_recycle=3600,   # Recycle connections after 1 hour
    )

    # Add SQLite-specific pragmas for SQLite databases
    if "sqlite" in url:
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Create session factory
def create_session_factory(engine: Optional[Engine] = None) -> sessionmaker:
    """
    Create SQLAlchemy session factory.

    Args:
        engine: SQLAlchemy Engine. If None, creates new engine.

    Returns:
        sessionmaker instance
    """
    if engine is None:
        engine = create_db_engine()

    return sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )


# Global engine and session factory (for convenience)
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """Get or create global database engine."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create global session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


def get_session() -> Session:
    """Get new database session."""
    factory = get_session_factory()
    return factory()


def init_db() -> None:
    """
    Initialize database by creating all tables.

    This should be called once at application startup or during setup.
    """
    from src.db.models import Base

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def drop_db() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data. Use only for testing/development.
    """
    from src.db.models import Base

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped successfully")
