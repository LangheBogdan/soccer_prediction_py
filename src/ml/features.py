"""
Feature engineering for ML model training and prediction.

This module provides functions to extract and engineer features from the database
for use in match outcome prediction models.
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from src.db.models import Match, MatchStatus, TeamStats, PredictionOutcome

logger = logging.getLogger(__name__)


def get_recent_matches(
    session: Session, team_id: int, num_matches: int = 10, before_date: Optional[datetime] = None
) -> list[Match]:
    """
    Get the most recent matches for a team.

    Args:
        session: SQLAlchemy session
        team_id: Team ID
        num_matches: Number of recent matches to retrieve
        before_date: Only consider matches before this date (defaults to now)

    Returns:
        List of Match objects ordered by date (most recent first)
    """
    if before_date is None:
        before_date = datetime.utcnow()

    matches = (
        session.query(Match)
        .filter(
            Match.status == MatchStatus.FINISHED,
            Match.match_date < before_date,
            ((Match.home_team_id == team_id) | (Match.away_team_id == team_id))
        )
        .order_by(Match.match_date.desc())
        .limit(num_matches)
        .all()
    )

    return matches


def get_head_to_head(
    session: Session,
    home_team_id: int,
    away_team_id: int,
    num_matches: int = 5,
    before_date: Optional[datetime] = None,
) -> list[Match]:
    """
    Get head-to-head matches between two teams.

    Args:
        session: SQLAlchemy session
        home_team_id: Home team ID
        away_team_id: Away team ID
        num_matches: Number of H2H matches to retrieve
        before_date: Only consider matches before this date

    Returns:
        List of Match objects ordered by date (most recent first)
    """
    if before_date is None:
        before_date = datetime.utcnow()

    matches = (
        session.query(Match)
        .filter(
            Match.status == MatchStatus.FINISHED,
            Match.match_date < before_date,
            (
                ((Match.home_team_id == home_team_id) & (Match.away_team_id == away_team_id))
                | ((Match.home_team_id == away_team_id) & (Match.away_team_id == home_team_id))
            )
        )
        .order_by(Match.match_date.desc())
        .limit(num_matches)
        .all()
    )

    return matches


def calculate_team_stats(
    session: Session,
    team_id: int,
    num_matches: int = 10,
    before_date: Optional[datetime] = None,
) -> Dict[str, float]:
    """
    Calculate team statistics from recent matches.

    Args:
        session: SQLAlchemy session
        team_id: Team ID
        num_matches: Number of recent matches to use
        before_date: Only consider matches before this date

    Returns:
        Dictionary with team statistics
    """
    matches = get_recent_matches(session, team_id, num_matches, before_date)

    if not matches:
        return {
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "draw_rate": 0.0,
            "avg_goals_for": 0.0,
            "avg_goals_against": 0.0,
            "avg_shots": 0.0,
            "avg_shots_on_target": 0.0,
            "avg_possession": 0.0,
            "matches_played": 0,
        }

    wins = 0
    losses = 0
    draws = 0
    goals_for = 0
    goals_against = 0
    shots = 0
    shots_on_target = 0
    possession_sum = 0
    valid_possession_count = 0

    for match in matches:
        is_home = match.home_team_id == team_id

        if is_home:
            match_goals_for = match.home_goals or 0
            match_goals_against = match.away_goals or 0
            match_shots = match.home_shots or 0
            match_shots_on_target = match.home_shots_on_target or 0
            match_possession = match.home_possession or 0
        else:
            match_goals_for = match.away_goals or 0
            match_goals_against = match.home_goals or 0
            match_shots = match.away_shots or 0
            match_shots_on_target = match.away_shots_on_target or 0
            match_possession = match.away_possession or 0

        goals_for += match_goals_for
        goals_against += match_goals_against
        shots += match_shots
        shots_on_target += match_shots_on_target

        if match_possession > 0:
            possession_sum += match_possession
            valid_possession_count += 1

        if match_goals_for > match_goals_against:
            wins += 1
        elif match_goals_for < match_goals_against:
            losses += 1
        else:
            draws += 1

    num_matches_played = len(matches)

    return {
        "win_rate": wins / num_matches_played if num_matches_played > 0 else 0.0,
        "loss_rate": losses / num_matches_played if num_matches_played > 0 else 0.0,
        "draw_rate": draws / num_matches_played if num_matches_played > 0 else 0.0,
        "avg_goals_for": goals_for / num_matches_played if num_matches_played > 0 else 0.0,
        "avg_goals_against": goals_against / num_matches_played if num_matches_played > 0 else 0.0,
        "avg_shots": shots / num_matches_played if num_matches_played > 0 else 0.0,
        "avg_shots_on_target": shots_on_target / num_matches_played if num_matches_played > 0 else 0.0,
        "avg_possession": possession_sum / valid_possession_count if valid_possession_count > 0 else 0.0,
        "matches_played": num_matches_played,
    }


def calculate_h2h_stats(
    session: Session,
    home_team_id: int,
    away_team_id: int,
    num_matches: int = 5,
    before_date: Optional[datetime] = None,
) -> Dict[str, float]:
    """
    Calculate head-to-head statistics between two teams.

    Args:
        session: SQLAlchemy session
        home_team_id: Home team ID
        away_team_id: Away team ID
        num_matches: Number of H2H matches to use
        before_date: Only consider matches before this date

    Returns:
        Dictionary with H2H statistics
    """
    matches = get_head_to_head(session, home_team_id, away_team_id, num_matches, before_date)

    if not matches:
        return {
            "h2h_home_wins": 0,
            "h2h_draws": 0,
            "h2h_away_wins": 0,
            "h2h_home_avg_goals": 0.0,
            "h2h_away_avg_goals": 0.0,
        }

    home_wins = 0
    away_wins = 0
    draws = 0
    home_goals_sum = 0
    away_goals_sum = 0

    for match in matches:
        home_goals = match.home_goals or 0
        away_goals = match.away_goals or 0

        home_goals_sum += home_goals
        away_goals_sum += away_goals

        if home_goals > away_goals:
            if match.home_team_id == home_team_id:
                home_wins += 1
            else:
                away_wins += 1
        elif home_goals < away_goals:
            if match.home_team_id == home_team_id:
                away_wins += 1
            else:
                home_wins += 1
        else:
            draws += 1

    num_matches = len(matches)

    return {
        "h2h_home_wins": home_wins,
        "h2h_draws": draws,
        "h2h_away_wins": away_wins,
        "h2h_home_avg_goals": home_goals_sum / num_matches if num_matches > 0 else 0.0,
        "h2h_away_avg_goals": away_goals_sum / num_matches if num_matches > 0 else 0.0,
    }


def extract_match_features(
    session: Session, match: Match, recent_matches: int = 10, h2h_matches: int = 5
) -> Dict[str, float]:
    """
    Extract all features for a match for ML prediction.

    Args:
        session: SQLAlchemy session
        match: Match object
        recent_matches: Number of recent matches to use for stats
        h2h_matches: Number of H2H matches to use

    Returns:
        Dictionary with all extracted features
    """
    features = {}

    # Get team statistics (only consider matches before this one)
    home_stats = calculate_team_stats(
        session, match.home_team_id, recent_matches, match.match_date
    )
    away_stats = calculate_team_stats(
        session, match.away_team_id, recent_matches, match.match_date
    )

    # Get H2H statistics
    h2h_stats = calculate_h2h_stats(
        session, match.home_team_id, match.away_team_id, h2h_matches, match.match_date
    )

    # Home team features
    features["home_win_rate"] = home_stats["win_rate"]
    features["home_draw_rate"] = home_stats["draw_rate"]
    features["home_loss_rate"] = home_stats["loss_rate"]
    features["home_avg_goals_for"] = home_stats["avg_goals_for"]
    features["home_avg_goals_against"] = home_stats["avg_goals_against"]
    features["home_avg_shots"] = home_stats["avg_shots"]
    features["home_avg_shots_on_target"] = home_stats["avg_shots_on_target"]
    features["home_avg_possession"] = home_stats["avg_possession"]
    features["home_matches_played"] = float(home_stats["matches_played"])

    # Away team features
    features["away_win_rate"] = away_stats["win_rate"]
    features["away_draw_rate"] = away_stats["draw_rate"]
    features["away_loss_rate"] = away_stats["loss_rate"]
    features["away_avg_goals_for"] = away_stats["avg_goals_for"]
    features["away_avg_goals_against"] = away_stats["avg_goals_against"]
    features["away_avg_shots"] = away_stats["avg_shots"]
    features["away_avg_shots_on_target"] = away_stats["avg_shots_on_target"]
    features["away_avg_possession"] = away_stats["avg_possession"]
    features["away_matches_played"] = float(away_stats["matches_played"])

    # Relative features (home vs away)
    features["goal_difference"] = features["home_avg_goals_for"] - features["away_avg_goals_for"]
    features["possession_difference"] = features["home_avg_possession"] - features["away_avg_possession"]
    features["win_rate_difference"] = features["home_win_rate"] - features["away_win_rate"]

    # H2H features
    features["h2h_home_wins"] = float(h2h_stats["h2h_home_wins"])
    features["h2h_draws"] = float(h2h_stats["h2h_draws"])
    features["h2h_away_wins"] = float(h2h_stats["h2h_away_wins"])
    features["h2h_home_avg_goals"] = h2h_stats["h2h_home_avg_goals"]
    features["h2h_away_avg_goals"] = h2h_stats["h2h_away_avg_goals"]

    # Match context
    features["is_home_advantage"] = 1.0  # Always 1 for home team in home match

    return features


def create_training_dataset(
    session: Session, min_matches: int = 500, recent_matches: int = 10, h2h_matches: int = 5
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Create a training dataset from historical matches.

    Args:
        session: SQLAlchemy session
        min_matches: Minimum number of finished matches required
        recent_matches: Number of recent matches to use for stats
        h2h_matches: Number of H2H matches to use

    Returns:
        Tuple of (features DataFrame, target Series)
    """
    # Get all finished matches
    finished_matches = (
        session.query(Match)
        .filter(Match.status == MatchStatus.FINISHED)
        .order_by(Match.match_date.asc())
        .all()
    )

    if len(finished_matches) < min_matches:
        raise ValueError(
            f"Not enough finished matches. Found {len(finished_matches)}, "
            f"need at least {min_matches}"
        )

    logger.info(f"Creating training dataset from {len(finished_matches)} finished matches")

    feature_list = []
    target_list = []
    skipped = 0

    for match in finished_matches:
        try:
            # Skip matches without final scores
            if match.home_goals is None or match.away_goals is None:
                skipped += 1
                continue

            # Extract features
            features = extract_match_features(
                session, match, recent_matches, h2h_matches
            )
            feature_list.append(features)

            # Determine outcome (target)
            if match.home_goals > match.away_goals:
                outcome = PredictionOutcome.HOME_WIN
            elif match.home_goals < match.away_goals:
                outcome = PredictionOutcome.AWAY_WIN
            else:
                outcome = PredictionOutcome.DRAW

            target_list.append(outcome.value)

        except Exception as e:
            logger.warning(f"Error extracting features for match {match.id}: {e}")
            skipped += 1
            continue

    logger.info(
        f"Created dataset with {len(feature_list)} samples "
        f"({skipped} matches skipped)"
    )

    # Convert to DataFrame
    X = pd.DataFrame(feature_list)
    y = pd.Series(target_list)

    # Fill any NaN values with 0
    X = X.fillna(0.0)

    return X, y


def get_feature_names() -> list[str]:
    """Get list of all feature names in consistent order."""
    return [
        # Home team features
        "home_win_rate",
        "home_draw_rate",
        "home_loss_rate",
        "home_avg_goals_for",
        "home_avg_goals_against",
        "home_avg_shots",
        "home_avg_shots_on_target",
        "home_avg_possession",
        "home_matches_played",
        # Away team features
        "away_win_rate",
        "away_draw_rate",
        "away_loss_rate",
        "away_avg_goals_for",
        "away_avg_goals_against",
        "away_avg_shots",
        "away_avg_shots_on_target",
        "away_avg_possession",
        "away_matches_played",
        # Relative features
        "goal_difference",
        "possession_difference",
        "win_rate_difference",
        # H2H features
        "h2h_home_wins",
        "h2h_draws",
        "h2h_away_wins",
        "h2h_home_avg_goals",
        "h2h_away_avg_goals",
        # Context
        "is_home_advantage",
    ]
