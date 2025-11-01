"""
Database models for the Soccer Prediction application.

This module defines SQLAlchemy ORM models for:
- Leagues, Teams, and Matches
- Historical statistics and performance metrics
- Betting odds from external sources
- User predictions and results
- Performance tracking
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Boolean,
    Date,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class LeagueType(str, Enum):
    """Type of football league"""
    DOMESTIC = "domestic"
    INTERNATIONAL = "international"
    CUP = "cup"


class MatchStatus(str, Enum):
    """Status of a match"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class PredictionOutcome(str, Enum):
    """Prediction outcome types"""
    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"


class League(Base):
    """Football league information"""
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    country = Column(String(100), nullable=False)
    season = Column(String(9), nullable=False)  # e.g., "2023-24"
    league_type = Column(SQLEnum(LeagueType), default=LeagueType.DOMESTIC)
    external_id = Column(String(100), unique=True, nullable=True)  # For API tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teams = relationship("Team", back_populates="league", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="league", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_league_country_season", "country", "season"),
    )


class Team(Base):
    """Football team information"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    founded_year = Column(Integer, nullable=True)
    external_id = Column(String(100), nullable=True)  # For API tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    league = relationship("League", back_populates="teams")
    home_matches = relationship(
        "Match", foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    away_matches = relationship(
        "Match", foreign_keys="Match.away_team_id", back_populates="away_team"
    )
    team_stats = relationship("TeamStats", back_populates="team", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_team_league_id", "league_id"),
        Index("ix_team_name", "name"),
    )


class Match(Base):
    """Football match data"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    match_date = Column(DateTime, nullable=False)
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    status = Column(SQLEnum(MatchStatus), default=MatchStatus.SCHEDULED)
    home_shots = Column(Integer, nullable=True)
    away_shots = Column(Integer, nullable=True)
    home_shots_on_target = Column(Integer, nullable=True)
    away_shots_on_target = Column(Integer, nullable=True)
    home_possession = Column(Float, nullable=True)  # Percentage
    away_possession = Column(Float, nullable=True)
    home_passes = Column(Integer, nullable=True)
    away_passes = Column(Integer, nullable=True)
    home_pass_accuracy = Column(Float, nullable=True)  # Percentage
    away_pass_accuracy = Column(Float, nullable=True)
    home_fouls = Column(Integer, nullable=True)
    away_fouls = Column(Integer, nullable=True)
    home_yellow_cards = Column(Integer, nullable=True)
    away_yellow_cards = Column(Integer, nullable=True)
    home_red_cards = Column(Integer, nullable=True)
    away_red_cards = Column(Integer, nullable=True)
    external_id = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    league = relationship("League", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    odds = relationship("Odds", back_populates="match", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="match", cascade="all, delete-orphan")
    match_stats = relationship("MatchStats", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_match_league_date", "league_id", "match_date"),
        Index("ix_match_status", "status"),
        Index("ix_match_external_id", "external_id"),
    )


class TeamStats(Base):
    """Historical team statistics"""
    __tablename__ = "team_stats"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(String(9), nullable=False)
    matches_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_difference = Column(Integer, default=0)
    points = Column(Integer, default=0)
    avg_possession = Column(Float, nullable=True)
    avg_shots = Column(Float, nullable=True)
    avg_shots_on_target = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="team_stats")

    __table_args__ = (
        Index("ix_team_stats_team_season", "team_id", "season"),
    )


class MatchStats(Base):
    """Detailed statistics for individual matches (from various sources)"""
    __tablename__ = "match_stats"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    source = Column(String(50), nullable=False)  # e.g., 'fbref', 'api_football'
    data_json = Column(Text, nullable=True)  # Store raw data as JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    match = relationship("Match", back_populates="match_stats")

    __table_args__ = (
        Index("ix_match_stats_match_id", "match_id"),
        Index("ix_match_stats_source", "source"),
    )


class Odds(Base):
    """Betting odds from various bookmakers"""
    __tablename__ = "odds"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    bookmaker = Column(String(100), nullable=False)
    home_win_odds = Column(Numeric(6, 2), nullable=False)
    draw_odds = Column(Numeric(6, 2), nullable=False)
    away_win_odds = Column(Numeric(6, 2), nullable=False)
    over_2_5_odds = Column(Numeric(6, 2), nullable=True)
    under_2_5_odds = Column(Numeric(6, 2), nullable=True)
    retrieved_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    match = relationship("Match", back_populates="odds")

    __table_args__ = (
        Index("ix_odds_match_bookmaker", "match_id", "bookmaker"),
        Index("ix_odds_retrieved_at", "retrieved_at"),
    )


class User(Base):
    """User account for prediction tracking"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_user_username", "username"),
        Index("ix_user_email", "email"),
    )


class Prediction(Base):
    """User predictions for matches"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    predicted_outcome = Column(SQLEnum(PredictionOutcome), nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    stake = Column(Numeric(10, 2), nullable=True)  # Betting stake
    odds_used = Column(Numeric(6, 2), nullable=True)  # Odds at time of prediction
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="predictions")
    match = relationship("Match", back_populates="predictions")
    result = relationship("PredictionResult", back_populates="prediction", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_prediction_user_id", "user_id"),
        Index("ix_prediction_match_id", "match_id"),
        Index("ix_prediction_created_at", "created_at"),
    )


class PredictionResult(Base):
    """Results and accuracy metrics for predictions"""
    __tablename__ = "prediction_results"

    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False, unique=True)
    actual_outcome = Column(SQLEnum(PredictionOutcome), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    profit_loss = Column(Numeric(10, 2), nullable=True)  # P/L if stake was recorded
    return_rate = Column(Float, nullable=True)  # ROI percentage
    evaluated_at = Column(DateTime, nullable=False)

    # Relationships
    prediction = relationship("Prediction", back_populates="result")

    __table_args__ = (
        Index("ix_prediction_result_prediction_id", "prediction_id"),
        Index("ix_prediction_result_is_correct", "is_correct"),
    )


class ModelMetrics(Base):
    """ML model performance metrics for historical tracking"""
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True)
    model_version = Column(String(50), nullable=False)
    training_date = Column(DateTime, nullable=False)
    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    auc_score = Column(Float, nullable=True)
    samples_used = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_model_metrics_version", "model_version"),
        Index("ix_model_metrics_training_date", "training_date"),
    )
