"""
Tests for database models and configuration.

This test suite verifies:
- Database model creation and relationships
- Session management
- Data persistence and retrieval
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.db.models import (
    Base,
    League,
    Team,
    Match,
    TeamStats,
    Odds,
    User,
    Prediction,
    PredictionResult,
    LeagueType,
    MatchStatus,
    PredictionOutcome,
)
from src.db.config import get_database_url, create_db_engine, create_session_factory


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        yield SessionLocal
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session(temp_db):
    """Get database session for tests."""
    db = temp_db()
    try:
        yield db
    finally:
        db.close()


class TestDatabaseModels:
    """Test database model creation and relationships."""

    def test_create_league(self, session):
        """Test creating a league."""
        league = League(
            name="Premier League",
            country="England",
            season="2024-25",
            league_type=LeagueType.DOMESTIC,
        )
        session.add(league)
        session.commit()

        retrieved = session.query(League).filter_by(name="Premier League").first()
        assert retrieved is not None
        assert retrieved.country == "England"
        assert retrieved.season == "2024-25"

    def test_create_team(self, session):
        """Test creating a team with league relationship."""
        league = League(
            name="Premier League",
            country="England",
            season="2024-25",
        )
        session.add(league)
        session.commit()

        team = Team(
            name="Manchester United",
            country="England",
            league_id=league.id,
            founded_year=1878,
        )
        session.add(team)
        session.commit()

        retrieved = session.query(Team).filter_by(name="Manchester United").first()
        assert retrieved is not None
        assert retrieved.league_id == league.id
        assert retrieved.league.name == "Premier League"

    def test_create_match(self, session):
        """Test creating a match with team relationships."""
        league = League(
            name="Premier League",
            country="England",
            season="2024-25",
        )
        session.add(league)
        session.commit()

        home_team = Team(
            name="Manchester United",
            country="England",
            league_id=league.id,
        )
        away_team = Team(
            name="Liverpool",
            country="England",
            league_id=league.id,
        )
        session.add_all([home_team, away_team])
        session.commit()

        match = Match(
            league_id=league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=datetime.utcnow() + timedelta(days=7),
            status=MatchStatus.SCHEDULED,
            home_shots=10,
            away_shots=8,
            home_possession=55.0,
            away_possession=45.0,
        )
        session.add(match)
        session.commit()

        retrieved = session.query(Match).first()
        assert retrieved is not None
        assert retrieved.home_team.name == "Manchester United"
        assert retrieved.away_team.name == "Liverpool"
        assert retrieved.league.name == "Premier League"

    def test_match_with_results(self, session):
        """Test match with goals and final status."""
        league = League(name="Premier League", country="England", season="2024-25")
        session.add(league)
        session.commit()

        home_team = Team(name="Man United", country="England", league_id=league.id)
        away_team = Team(name="Arsenal", country="England", league_id=league.id)
        session.add_all([home_team, away_team])
        session.commit()

        match = Match(
            league_id=league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=datetime.utcnow() - timedelta(days=1),
            status=MatchStatus.FINISHED,
            home_goals=2,
            away_goals=1,
        )
        session.add(match)
        session.commit()

        retrieved = session.query(Match).first()
        assert retrieved.home_goals == 2
        assert retrieved.away_goals == 1
        assert retrieved.status == MatchStatus.FINISHED

    def test_team_stats(self, session):
        """Test team statistics."""
        league = League(name="Premier League", country="England", season="2024-25")
        session.add(league)
        session.commit()

        team = Team(name="Chelsea", country="England", league_id=league.id)
        session.add(team)
        session.commit()

        stats = TeamStats(
            team_id=team.id,
            season="2024-25",
            matches_played=10,
            wins=7,
            draws=2,
            losses=1,
            goals_for=25,
            goals_against=8,
            points=23,
            avg_possession=58.5,
        )
        session.add(stats)
        session.commit()

        retrieved = session.query(TeamStats).first()
        assert retrieved.matches_played == 10
        assert retrieved.wins == 7
        assert retrieved.points == 23
        assert retrieved.team.name == "Chelsea"

    def test_odds(self, session):
        """Test betting odds storage."""
        league = League(name="Premier League", country="England", season="2024-25")
        session.add(league)
        session.commit()

        home_team = Team(name="Man City", country="England", league_id=league.id)
        away_team = Team(name="Tottenham", country="England", league_id=league.id)
        session.add_all([home_team, away_team])
        session.commit()

        match = Match(
            league_id=league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=datetime.utcnow() + timedelta(days=7),
        )
        session.add(match)
        session.commit()

        odds = Odds(
            match_id=match.id,
            bookmaker="Bet365",
            home_win_odds=1.80,
            draw_odds=3.50,
            away_win_odds=4.20,
            retrieved_at=datetime.utcnow(),
        )
        session.add(odds)
        session.commit()

        retrieved = session.query(Odds).first()
        assert retrieved.bookmaker == "Bet365"
        assert float(retrieved.home_win_odds) == pytest.approx(1.80, rel=0.01)
        assert retrieved.match.home_team.name == "Man City"

    def test_user_and_prediction(self, session):
        """Test user creation and predictions."""
        league = League(name="Premier League", country="England", season="2024-25")
        session.add(league)
        session.commit()

        home_team = Team(name="Liverpool", country="England", league_id=league.id)
        away_team = Team(name="Everton", country="England", league_id=league.id)
        session.add_all([home_team, away_team])
        session.commit()

        match = Match(
            league_id=league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=datetime.utcnow() + timedelta(days=7),
        )
        session.add(match)
        session.commit()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
        )
        session.add(user)
        session.commit()

        prediction = Prediction(
            user_id=user.id,
            match_id=match.id,
            predicted_outcome=PredictionOutcome.HOME_WIN,
            confidence=0.75,
            stake=10.00,
            odds_used=1.80,
        )
        session.add(prediction)
        session.commit()

        retrieved = session.query(Prediction).first()
        assert retrieved.user.username == "testuser"
        assert retrieved.match.home_team.name == "Liverpool"
        assert retrieved.predicted_outcome == PredictionOutcome.HOME_WIN
        assert retrieved.confidence == 0.75

    def test_prediction_result(self, session):
        """Test prediction results and accuracy tracking."""
        league = League(name="Premier League", country="England", season="2024-25")
        session.add(league)
        session.commit()

        home_team = Team(name="Man United", country="England", league_id=league.id)
        away_team = Team(name="Chelsea", country="England", league_id=league.id)
        session.add_all([home_team, away_team])
        session.commit()

        match = Match(
            league_id=league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=datetime.utcnow() - timedelta(days=1),
            status=MatchStatus.FINISHED,
            home_goals=2,
            away_goals=1,
        )
        session.add(match)
        session.commit()

        user = User(
            username="predictor",
            email="predictor@example.com",
            password_hash="hashed",
        )
        session.add(user)
        session.commit()

        prediction = Prediction(
            user_id=user.id,
            match_id=match.id,
            predicted_outcome=PredictionOutcome.HOME_WIN,
            confidence=0.80,
            stake=20.00,
            odds_used=2.00,
        )
        session.add(prediction)
        session.commit()

        result = PredictionResult(
            prediction_id=prediction.id,
            actual_outcome=PredictionOutcome.HOME_WIN,
            is_correct=True,
            profit_loss=20.00,
            return_rate=100.0,
            evaluated_at=datetime.utcnow(),
        )
        session.add(result)
        session.commit()

        retrieved = session.query(PredictionResult).first()
        assert retrieved.is_correct is True
        assert retrieved.prediction.user.username == "predictor"
        assert retrieved.profit_loss == 20.00

    def test_cascade_delete(self, session):
        """Test cascade delete behavior."""
        league = League(name="Test League", country="Test", season="2024-25")
        session.add(league)
        session.commit()

        team = Team(name="Test Team", country="Test", league_id=league.id)
        session.add(team)
        session.commit()

        session.delete(league)
        session.commit()

        # League should be deleted
        assert session.query(League).filter_by(name="Test League").first() is None
        # Team should also be deleted due to cascade
        assert session.query(Team).filter_by(name="Test Team").first() is None

    def test_database_url_config(self):
        """Test database URL configuration."""
        # Should return a valid URL
        url = get_database_url()
        assert isinstance(url, str)
        assert len(url) > 0

    def test_create_engine(self):
        """Test engine creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_url = f"sqlite:///{db_path}"
            engine = create_db_engine(db_url)
            assert engine is not None
            assert str(engine.url) == db_url


class TestDataIntegrity:
    """Test data integrity and constraints."""

    def test_unique_league_name(self, session):
        """Test unique constraint on league name."""
        league1 = League(name="Unique League", country="Country1", season="2024-25")
        league2 = League(name="Unique League", country="Country2", season="2024-25")

        session.add(league1)
        session.commit()

        session.add(league2)
        with pytest.raises(Exception):  # Should raise integrity error
            session.commit()

    def test_foreign_key_constraint(self, session):
        """Test foreign key constraints."""
        # Try to create team with non-existent league
        team = Team(name="Orphan Team", country="Country", league_id=9999)
        session.add(team)

        with pytest.raises(Exception):
            session.commit()

    def test_timestamps(self, session):
        """Test automatic timestamp creation."""
        league = League(name="Timestamp Test", country="Country", season="2024-25")
        session.add(league)
        session.commit()

        retrieved = session.query(League).first()
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
        assert retrieved.created_at <= retrieved.updated_at
