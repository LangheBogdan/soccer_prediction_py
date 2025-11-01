"""Database module - SQLAlchemy models, session management, and database queries."""

from src.db.config import (
    get_database_url,
    get_engine,
    get_session_factory,
    get_session,
    init_db,
    drop_db,
    create_db_engine,
    create_session_factory,
)
from src.db.models import (
    Base,
    League,
    Team,
    Match,
    TeamStats,
    MatchStats,
    Odds,
    User,
    Prediction,
    PredictionResult,
    ModelMetrics,
    LeagueType,
    MatchStatus,
    PredictionOutcome,
)

__all__ = [
    # Config
    "get_database_url",
    "get_engine",
    "get_session_factory",
    "get_session",
    "init_db",
    "drop_db",
    "create_db_engine",
    "create_session_factory",
    # Models
    "Base",
    "League",
    "Team",
    "Match",
    "TeamStats",
    "MatchStats",
    "Odds",
    "User",
    "Prediction",
    "PredictionResult",
    "ModelMetrics",
    # Enums
    "LeagueType",
    "MatchStatus",
    "PredictionOutcome",
]