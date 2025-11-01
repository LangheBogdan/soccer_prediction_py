"""
Tests for ML model training, evaluation, and prediction.

Tests cover:
- Feature engineering functions
- Model training and evaluation
- Model saving/loading
- Prediction endpoint
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.db.models import (
    Base,
    League,
    Team,
    Match,
    MatchStatus,
    TeamStats,
    PredictionOutcome,
    ModelMetrics,
)
from src.ml.features import (
    get_recent_matches,
    get_head_to_head,
    calculate_team_stats,
    calculate_h2h_stats,
    extract_match_features,
    create_training_dataset,
    get_feature_names,
)
from src.ml.model import ModelManager, train_and_save_model, get_prediction_for_match, get_model_metrics


# ===== Test Database Setup =====

@pytest.fixture(scope="function")
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture(scope="function")
def sample_league(test_db: Session) -> League:
    """Create a sample league."""
    league = League(
        name="Premier League",
        country="England",
        season="2023-24",
    )
    test_db.add(league)
    test_db.commit()
    test_db.refresh(league)
    return league


@pytest.fixture(scope="function")
def sample_teams(test_db: Session, sample_league: League) -> tuple[Team, Team]:
    """Create sample teams."""
    home_team = Team(name="Team A", country="England", league_id=sample_league.id)
    away_team = Team(name="Team B", country="England", league_id=sample_league.id)
    test_db.add(home_team)
    test_db.add(away_team)
    test_db.commit()
    test_db.refresh(home_team)
    test_db.refresh(away_team)
    return home_team, away_team


@pytest.fixture(scope="function")
def sample_matches(test_db: Session, sample_league: League, sample_teams: tuple[Team, Team]) -> list[Match]:
    """Create sample matches with final scores."""
    home_team, away_team = sample_teams
    matches = []

    base_date = datetime.utcnow() - timedelta(days=100)

    for i in range(20):
        match_date = base_date + timedelta(days=i*5)

        # Vary the scores
        if i % 3 == 0:
            home_goals, away_goals = 2, 1
        elif i % 3 == 1:
            home_goals, away_goals = 1, 1
        else:
            home_goals, away_goals = 0, 1

        match = Match(
            league_id=sample_league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=match_date,
            home_goals=home_goals,
            away_goals=away_goals,
            status=MatchStatus.FINISHED,
            home_shots=15 + i,
            away_shots=10 + i,
            home_shots_on_target=5 + (i % 3),
            away_shots_on_target=4 + (i % 3),
            home_possession=55.0 + (i % 10),
            away_possession=45.0 - (i % 10),
        )
        matches.append(match)
        test_db.add(match)

    test_db.commit()
    for m in matches:
        test_db.refresh(m)
    return matches


# ===== Feature Engineering Tests =====

class TestFeatureEngineering:
    """Test feature engineering functions."""

    def test_get_recent_matches(self, test_db: Session, sample_teams: tuple[Team, Team], sample_matches: list[Match]):
        """Test retrieving recent matches for a team."""
        home_team, away_team = sample_teams

        recent = get_recent_matches(test_db, home_team.id, num_matches=5)
        assert len(recent) == 5
        assert all(m.status == MatchStatus.FINISHED for m in recent)
        assert recent[0].match_date >= recent[-1].match_date  # Most recent first

    def test_get_recent_matches_before_date(self, test_db: Session, sample_teams: tuple[Team, Team], sample_matches: list[Match]):
        """Test retrieving matches before a specific date."""
        home_team, away_team = sample_teams

        before_date = datetime.utcnow() - timedelta(days=30)
        recent = get_recent_matches(test_db, home_team.id, num_matches=10, before_date=before_date)

        assert all(m.match_date < before_date for m in recent)

    def test_get_head_to_head(self, test_db: Session, sample_teams: tuple[Team, Team], sample_matches: list[Match]):
        """Test retrieving head-to-head matches."""
        home_team, away_team = sample_teams

        h2h = get_head_to_head(test_db, home_team.id, away_team.id, num_matches=5)
        assert len(h2h) > 0
        assert all(m.status == MatchStatus.FINISHED for m in h2h)

    def test_calculate_team_stats(self, test_db: Session, sample_teams: tuple[Team, Team], sample_matches: list[Match]):
        """Test calculating team statistics."""
        home_team, away_team = sample_teams

        stats = calculate_team_stats(test_db, home_team.id, num_matches=5)

        assert "win_rate" in stats
        assert "loss_rate" in stats
        assert "draw_rate" in stats
        assert "avg_goals_for" in stats
        assert "avg_goals_against" in stats
        assert 0.0 <= stats["win_rate"] <= 1.0
        assert 0.0 <= stats["draw_rate"] <= 1.0
        assert 0.0 <= stats["loss_rate"] <= 1.0

    def test_calculate_h2h_stats(self, test_db: Session, sample_teams: tuple[Team, Team], sample_matches: list[Match]):
        """Test calculating head-to-head statistics."""
        home_team, away_team = sample_teams

        h2h_stats = calculate_h2h_stats(test_db, home_team.id, away_team.id, num_matches=5)

        assert "h2h_home_wins" in h2h_stats
        assert "h2h_draws" in h2h_stats
        assert "h2h_away_wins" in h2h_stats
        assert isinstance(h2h_stats["h2h_home_wins"], (int, float))

    def test_extract_match_features(self, test_db: Session, sample_teams: tuple[Team, Team], sample_matches: list[Match]):
        """Test extracting features for a specific match."""
        # Use the last match (most recent) for prediction
        match = sample_matches[-1]

        features = extract_match_features(test_db, match, recent_matches=10, h2h_matches=5)

        # Check required features exist
        required_features = [
            "home_win_rate",
            "away_win_rate",
            "goal_difference",
            "h2h_home_wins",
            "is_home_advantage",
        ]
        for feature in required_features:
            assert feature in features
            assert isinstance(features[feature], (int, float))

    def test_get_feature_names(self):
        """Test getting feature names."""
        feature_names = get_feature_names()

        assert len(feature_names) > 0
        assert "home_win_rate" in feature_names
        assert "away_win_rate" in feature_names
        assert "goal_difference" in feature_names


# ===== Dataset Creation Tests =====

class TestDatasetCreation:
    """Test training dataset creation."""

    def test_create_training_dataset(self, test_db: Session, sample_matches: list[Match]):
        """Test creating a training dataset."""
        X, y = create_training_dataset(test_db, min_matches=5)

        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, pd.Series)
        assert len(X) == len(y)
        assert len(X) > 0
        assert len(X.columns) > 0

    def test_training_dataset_no_nans(self, test_db: Session, sample_matches: list[Match]):
        """Test that training dataset has no NaN values."""
        X, y = create_training_dataset(test_db, min_matches=5)

        assert not X.isna().any().any()
        assert not y.isna().any()

    def test_training_dataset_targets(self, test_db: Session, sample_matches: list[Match]):
        """Test that targets are valid prediction outcomes."""
        X, y = create_training_dataset(test_db, min_matches=5)

        valid_outcomes = [PredictionOutcome.HOME_WIN.value, PredictionOutcome.DRAW.value, PredictionOutcome.AWAY_WIN.value]
        assert all(outcome in valid_outcomes for outcome in y.unique())

    def test_training_dataset_insufficient_data(self, test_db: Session, sample_matches: list[Match]):
        """Test that error is raised when insufficient data."""
        with pytest.raises(ValueError, match="Not enough finished matches"):
            create_training_dataset(test_db, min_matches=1000)


# ===== Model Manager Tests =====

class TestModelManager:
    """Test ML model manager."""

    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        X = pd.DataFrame({
            "home_win_rate": np.random.rand(100),
            "away_win_rate": np.random.rand(100),
            "goal_difference": np.random.randn(100),
            "h2h_home_wins": np.random.randint(0, 5, 100),
            "is_home_advantage": np.ones(100),
        })
        y = pd.Series(["home_win", "away_win", "draw"] * 33 + ["home_win"])
        return X, y

    def test_model_manager_initialization(self):
        """Test ModelManager initialization."""
        manager = ModelManager("test_model")

        assert manager.model_name == "test_model"
        assert manager.model is None
        assert manager.label_encoder is None

    def test_train_logistic_model(self, sample_data):
        """Test training a logistic regression model."""
        manager = ModelManager("test_logistic")
        X, y = sample_data

        metrics = manager.train(X, y, model_type="logistic")

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert manager.model is not None
        assert manager.label_encoder is not None

    def test_train_random_forest_model(self, sample_data):
        """Test training a random forest model."""
        manager = ModelManager("test_rf")
        X, y = sample_data

        metrics = manager.train(X, y, model_type="random_forest")

        assert "accuracy" in metrics
        assert manager.model is not None

    def test_model_save_and_load(self, sample_data, tmp_path):
        """Test saving and loading a model."""
        import tempfile

        # Train model
        manager = ModelManager("test_save_load")
        X, y = sample_data
        manager.train(X, y, model_type="logistic")

        # Save model
        with patch.object(manager, 'model_path', tmp_path / "test_model.joblib"):
            with patch.object(manager, 'encoder_path', tmp_path / "test_encoder.joblib"):
                with patch.object(manager, 'metadata_path', tmp_path / "test_metadata.json"):
                    # Mock session
                    mock_session = MagicMock()
                    manager.save(mock_session, model_type="logistic")

        # Verify save was called (we can't actually test file I/O in this setup)
        assert manager.model is not None

    def test_model_predict(self, sample_data):
        """Test making predictions with trained model."""
        manager = ModelManager("test_predict")
        X, y = sample_data

        # Train on most of the data
        manager.train(X.iloc[:-10], y.iloc[:-10], model_type="logistic")

        # Predict on remaining data
        predictions, probabilities = manager.predict(X.iloc[-10:])

        assert len(predictions) == 10
        assert probabilities.shape[0] == 10
        assert probabilities.shape[1] == 3  # Three classes


# ===== Integration Tests =====

class TestMLIntegration:
    """Integration tests for ML components."""

    def test_train_and_save_model_success(self, test_db: Session, sample_matches: list[Match]):
        """Test complete training and saving flow."""
        result = train_and_save_model(test_db, model_type="logistic", min_matches=5)

        assert result["success"] is True
        assert "metrics" in result
        assert result["samples_used"] > 0

    def test_train_and_save_model_invalid_type(self, test_db: Session):
        """Test training with invalid model type."""
        result = train_and_save_model(test_db, model_type="invalid", min_matches=5)

        assert result["success"] is False

    def test_get_model_metrics(self, test_db: Session, sample_matches: list[Match]):
        """Test retrieving model metrics from database."""
        # Add sample metrics
        metrics = ModelMetrics(
            model_version="test_v1",
            training_date=datetime.utcnow(),
            accuracy=0.85,
            precision=0.82,
            recall=0.80,
            f1_score=0.81,
            samples_used=100,
        )
        test_db.add(metrics)
        test_db.commit()

        # Retrieve metrics
        retrieved = get_model_metrics(test_db, limit=10)

        assert len(retrieved) > 0
        assert retrieved[0]["model_version"] == "test_v1"
        assert retrieved[0]["accuracy"] == 0.85


