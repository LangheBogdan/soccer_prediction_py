"""
Unit tests for FastAPI endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.api.main import app
from src.api.dependencies import get_db
from src.db.models import Base, League, Team, Match, Odds, User, Prediction, MatchStatus

# Create test database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test client
client = TestClient(app)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_override(db):
    """Override the get_db dependency."""
    def override_get_db():
        return db

    app.dependency_overrides[get_db] = override_get_db
    yield db
    app.dependency_overrides.clear()


@pytest.fixture
def sample_league(db):
    """Create a sample league."""
    league = League(
        name="Premier League",
        country="England",
        season="2023-24",
        league_type="domestic",
        external_id="EPL",
    )
    db.add(league)
    db.commit()
    db.refresh(league)
    return league


@pytest.fixture
def sample_teams(db, sample_league):
    """Create sample teams."""
    teams = [
        Team(name="Manchester United", country="England", league_id=sample_league.id),
        Team(name="Liverpool", country="England", league_id=sample_league.id),
    ]
    for team in teams:
        db.add(team)
    db.commit()
    for team in teams:
        db.refresh(team)
    return teams


@pytest.fixture
def sample_match(db, sample_league, sample_teams):
    """Create a sample match."""
    match = Match(
        league_id=sample_league.id,
        home_team_id=sample_teams[0].id,
        away_team_id=sample_teams[1].id,
        match_date=datetime.utcnow() + timedelta(days=7),
        status=MatchStatus.SCHEDULED,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@pytest.fixture
def sample_user(db):
    """Create a sample user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ===== Health Check Tests =====

class TestHealthCheck:
    """Test health check endpoints."""

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Soccer Prediction API"
        assert data["status"] == "running"

    def test_health_check(self, test_db_override):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    def test_api_version(self):
        """Test API version endpoint."""
        response = client.get("/api/version")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "0.1.0"


# ===== League Endpoints Tests =====

class TestLeagueEndpoints:
    """Test league-related endpoints."""

    def test_get_leagues_empty(self, test_db_override):
        """Test getting leagues when none exist."""
        response = client.get("/api/leagues")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_leagues_with_data(self, test_db_override, sample_league):
        """Test getting leagues with data."""
        response = client.get("/api/leagues")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Premier League"

    def test_get_leagues_pagination(self, test_db_override, db, sample_league):
        """Test league pagination."""
        # Create additional leagues
        for i in range(5):
            league = League(
                name=f"League {i}",
                country="Country",
                season="2023-24",
            )
            db.add(league)
        db.commit()

        response = client.get("/api/leagues?skip=0&limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_get_league_by_id(self, test_db_override, sample_league):
        """Test getting a specific league."""
        response = client.get(f"/api/leagues/{sample_league.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Premier League"

    def test_get_league_not_found(self, test_db_override):
        """Test getting non-existent league."""
        response = client.get("/api/leagues/999")
        assert response.status_code == 404


# ===== Team Endpoints Tests =====

class TestTeamEndpoints:
    """Test team-related endpoints."""

    def test_get_league_teams(self, test_db_override, sample_league, sample_teams):
        """Test getting teams for a league."""
        response = client.get(f"/api/leagues/{sample_league.id}/teams")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Manchester United"

    def test_get_league_teams_not_found(self, test_db_override):
        """Test getting teams for non-existent league."""
        response = client.get("/api/leagues/999/teams")
        assert response.status_code == 404


# ===== Match Endpoints Tests =====

class TestMatchEndpoints:
    """Test match-related endpoints."""

    def test_get_matches_empty(self, test_db_override):
        """Test getting matches when none exist."""
        response = client.get("/api/matches")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_matches(self, test_db_override, sample_match):
        """Test getting matches."""
        response = client.get("/api/matches")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_matches_by_league(self, test_db_override, sample_match):
        """Test getting matches filtered by league."""
        response = client.get(f"/api/matches?league_id={sample_match.league_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_matches_by_status(self, test_db_override, sample_match):
        """Test getting matches filtered by status."""
        response = client.get("/api/matches?status=scheduled")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_matches_invalid_status(self, test_db_override):
        """Test getting matches with invalid status."""
        response = client.get("/api/matches?status=invalid_status")
        assert response.status_code == 400

    def test_get_match_detail(self, test_db_override, sample_match):
        """Test getting match details."""
        response = client.get(f"/api/matches/{sample_match.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_match.id

    def test_get_match_detail_not_found(self, test_db_override):
        """Test getting non-existent match."""
        response = client.get("/api/matches/999")
        assert response.status_code == 404

    def test_get_league_matches(self, test_db_override, sample_league, sample_match):
        """Test getting matches for a league."""
        response = client.get(f"/api/leagues/{sample_league.id}/matches")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


# ===== Odds Endpoints Tests =====

class TestOddsEndpoints:
    """Test odds-related endpoints."""

    def test_get_match_odds(self, test_db_override, sample_match, db):
        """Test getting odds for a match."""
        # Create odds
        odds = Odds(
            match_id=sample_match.id,
            bookmaker="Bet365",
            home_win_odds=2.50,
            draw_odds=3.00,
            away_win_odds=2.75,
            retrieved_at=datetime.utcnow(),
        )
        db.add(odds)
        db.commit()

        response = client.get(f"/api/odds/match/{sample_match.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["bookmaker"] == "Bet365"

    def test_get_match_odds_not_found(self, test_db_override):
        """Test getting odds for non-existent match."""
        response = client.get("/api/odds/match/999")
        assert response.status_code == 404

    def test_get_best_odds(self, test_db_override, sample_match, db):
        """Test getting best odds."""
        # Create multiple odds entries
        bookmakers = [
            ("Bet365", 2.50, 3.00, 2.75),
            ("DraftKings", 2.60, 2.95, 2.70),
            ("FanDuel", 2.55, 3.05, 2.80),
        ]

        for bm, hw, d, aw in bookmakers:
            odds = Odds(
                match_id=sample_match.id,
                bookmaker=bm,
                home_win_odds=hw,
                draw_odds=d,
                away_win_odds=aw,
                retrieved_at=datetime.utcnow(),
            )
            db.add(odds)
        db.commit()

        response = client.get(f"/api/odds/match/{sample_match.id}/best")
        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == sample_match.id
        assert "home_win" in data
        assert "draw" in data
        assert "away_win" in data

    def test_get_available_bookmakers(self, test_db_override, sample_match, db):
        """Test getting available bookmakers."""
        # Create odds with different bookmakers
        for bm in ["Bet365", "DraftKings", "FanDuel"]:
            odds = Odds(
                match_id=sample_match.id,
                bookmaker=bm,
                home_win_odds=2.50,
                draw_odds=3.00,
                away_win_odds=2.75,
                retrieved_at=datetime.utcnow(),
            )
            db.add(odds)
        db.commit()

        response = client.get("/api/odds/bookmakers")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert "Bet365" in data

    def test_compare_odds(self, test_db_override, sample_match, db):
        """Test odds comparison."""
        # Create odds
        odds = Odds(
            match_id=sample_match.id,
            bookmaker="Bet365",
            home_win_odds=2.50,
            draw_odds=3.00,
            away_win_odds=2.75,
            over_2_5_odds=1.95,
            under_2_5_odds=1.85,
            retrieved_at=datetime.utcnow(),
        )
        db.add(odds)
        db.commit()

        response = client.get(f"/api/odds/match/{sample_match.id}/comparison")
        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == sample_match.id
        assert "bookmakers" in data
        assert "Bet365" in data["bookmakers"]


# ===== Prediction Endpoints Tests =====

class TestPredictionEndpoints:
    """Test prediction-related endpoints."""

    def test_create_prediction(self, test_db_override, sample_user, sample_match):
        """Test creating a prediction."""
        prediction_data = {
            "user_id": sample_user.id,
            "match_id": sample_match.id,
            "predicted_outcome": "home_win",
            "confidence": 0.75,
        }

        response = client.post("/api/predictions", json=prediction_data)
        assert response.status_code == 201
        data = response.json()
        assert data["predicted_outcome"] == "home_win"

    def test_create_prediction_user_not_found(self, test_db_override, sample_match):
        """Test creating prediction for non-existent user."""
        prediction_data = {
            "user_id": 999,
            "match_id": sample_match.id,
            "predicted_outcome": "home_win",
            "confidence": 0.75,
        }

        response = client.post("/api/predictions", json=prediction_data)
        assert response.status_code == 404

    def test_create_prediction_match_not_found(self, test_db_override, sample_user):
        """Test creating prediction for non-existent match."""
        prediction_data = {
            "user_id": sample_user.id,
            "match_id": 999,
            "predicted_outcome": "home_win",
            "confidence": 0.75,
        }

        response = client.post("/api/predictions", json=prediction_data)
        assert response.status_code == 404

    def test_get_prediction(self, test_db_override, sample_user, sample_match, db):
        """Test getting a prediction."""
        # Create prediction
        prediction = Prediction(
            user_id=sample_user.id,
            match_id=sample_match.id,
            predicted_outcome="home_win",
            confidence=0.75,
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        response = client.get(f"/api/predictions/{prediction.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == prediction.id

    def test_get_user_predictions(self, test_db_override, sample_user, sample_match, db):
        """Test getting user predictions."""
        # Create predictions
        for i in range(3):
            prediction = Prediction(
                user_id=sample_user.id,
                match_id=sample_match.id,
                predicted_outcome="home_win",
                confidence=0.75,
            )
            db.add(prediction)
        db.commit()

        response = client.get(f"/api/predictions/user/{sample_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_user_stats(self, test_db_override, sample_user):
        """Test getting user stats."""
        response = client.get(f"/api/predictions/user/{sample_user.id}/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_predictions"] == 0
        assert data["accuracy"] == 0.0
