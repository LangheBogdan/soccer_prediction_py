"""
Database initialization script.

This script creates all database tables and can optionally seed initial data.
Usage: python -m src.db.init_db [--seed]
"""

import argparse
import sys
from pathlib import Path

from src.db.config import init_db, drop_db, get_session
from src.db.models import League, LeagueType


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
