"""
Database initialization script.

This script creates all database tables and can optionally seed initial data.
Usage: python -m src.db.init_db [--seed]
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from src.db.config import init_db, drop_db, get_session
from src.db.models import League, LeagueType, Team, Match, MatchStatus


def seed_initial_data():
    """Seed database with initial league data."""
    session = get_session()
    try:
        # Check if data already exists
        if session.query(League).count() > 0:
            print("Database already contains league data. Skipping seed.")
            return

        # Add sample leagues
        leagues = [
            League(
                name="Premier League",
                country="England",
                season="2024-25",
                league_type=LeagueType.DOMESTIC,
            ),
            League(
                name="La Liga",
                country="Spain",
                season="2024-25",
                league_type=LeagueType.DOMESTIC,
            ),
            League(
                name="Serie A",
                country="Italy",
                season="2024-25",
                league_type=LeagueType.DOMESTIC,
            ),
            League(
                name="Bundesliga",
                country="Germany",
                season="2024-25",
                league_type=LeagueType.DOMESTIC,
            ),
            League(
                name="Ligue 1",
                country="France",
                season="2024-25",
                league_type=LeagueType.DOMESTIC,
            ),
            League(
                name="UEFA Champions League",
                country="Europe",
                season="2024-25",
                league_type=LeagueType.INTERNATIONAL,
            ),
        ]

        session.add_all(leagues)
        session.commit()
        print(f"Seeded {len(leagues)} leagues")

    except Exception as e:
        session.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        session.close()


def seed_sample_data(session=None):
    """
    Seed database with sample teams and matches for ML training.

    Creates sample data with historical match results for model training.

    Args:
        session: Optional SQLAlchemy session. If None, creates a new one.
    """
    if session is None:
        session = get_session()

    try:
        # Get or create a league for the sample data
        league = session.query(League).filter(League.name == "Test League").first()
        if not league:
            league = League(
                name="Test League",
                country="Test",
                season="2024-25",
                league_type=LeagueType.DOMESTIC,
            )
            session.add(league)
            session.commit()

        # Create sample teams if they don't exist
        team_names = [
            "Team Alpha", "Team Beta", "Team Gamma", "Team Delta",
            "Team Epsilon", "Team Zeta", "Team Eta", "Team Theta",
        ]
        teams = []
        for name in team_names:
            team = session.query(Team).filter(
                Team.name == name, Team.league_id == league.id
            ).first()
            if not team:
                team = Team(name=name, country="Test", league_id=league.id)
                session.add(team)
            teams.append(team)

        session.commit()

        # Create sample historical matches
        match_count = session.query(Match).count()
        if match_count < 50:
            print(f"Seeding {50} historical matches...")
            base_date = datetime.utcnow() - timedelta(days=200)

            for i in range(50):
                match_date = base_date + timedelta(days=i*4)

                # Random teams and scores
                home_idx = i % len(teams)
                away_idx = (i + 1) % len(teams)

                # Vary the scores
                if i % 3 == 0:
                    home_goals, away_goals = 2, 1
                elif i % 3 == 1:
                    home_goals, away_goals = 1, 1
                else:
                    home_goals, away_goals = 1, 2

                match = Match(
                    league_id=league.id,
                    home_team_id=teams[home_idx].id,
                    away_team_id=teams[away_idx].id,
                    match_date=match_date,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    status=MatchStatus.FINISHED,
                    home_shots=15 + (i % 10),
                    away_shots=10 + (i % 10),
                    home_shots_on_target=5 + (i % 3),
                    away_shots_on_target=4 + (i % 3),
                    home_possession=55.0 + (i % 15),
                    away_possession=45.0 - (i % 15),
                    home_passes=400 + (i % 100),
                    away_passes=380 + (i % 100),
                    home_pass_accuracy=80.0 + (i % 10),
                    away_pass_accuracy=78.0 + (i % 10),
                )
                session.add(match)

            session.commit()
            print(f"✓ Seeded 50 historical matches")

    except Exception as e:
        session.rollback()
        print(f"Error seeding sample data: {e}")
        raise
    finally:
        session.close()


def main():
    """Run database initialization."""
    parser = argparse.ArgumentParser(description="Initialize database")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed database with initial data",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before creating (WARNING: destructive)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force drop without confirmation",
    )

    args = parser.parse_args()

    if args.drop:
        if not args.force:
            response = input(
                "⚠️  This will delete all database data. Continue? (yes/no): "
            )
            if response.lower() != "yes":
                print("Cancelled.")
                return

        drop_db()

    init_db()

    if args.seed:
        seed_initial_data()

    print("✓ Database initialization complete")


if __name__ == "__main__":
    main()
