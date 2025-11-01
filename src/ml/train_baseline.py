#!/usr/bin/env python3
"""
Script to train and serialize a baseline ML model for match prediction.

This script:
1. Creates a sample database with historical match data
2. Trains a logistic regression model
3. Saves the model and its metadata
4. Stores metrics in the database

Usage:
    python -m src.ml.train_baseline
"""

import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.db.models import Base
from src.db.init_db import seed_sample_data
from src.db.config import init_db
from src.ml.model import train_and_save_model


def train_baseline_model(database_url: str = "sqlite:///soccer_prediction.db") -> bool:
    """
    Train and save a baseline model.

    Args:
        database_url: Database connection URL

    Returns:
        True if successful, False otherwise
    """
    logger.info("=" * 70)
    logger.info("Training Baseline ML Model")
    logger.info("=" * 70)

    try:
        # Create database engine
        logger.info(f"Connecting to database: {database_url}")
        engine = create_engine(database_url, echo=False)

        # Initialize database schema
        logger.info("Creating database schema...")
        Base.metadata.create_all(engine)

        # Create session
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            # Check if we have data, if not seed sample data
            from src.db.models import Match

            match_count = session.query(Match).count()
            if match_count < 50:
                logger.info("Database is empty or has insufficient data. Seeding sample data...")
                seed_sample_data(session)
                match_count = session.query(Match).count()
                logger.info(f"Seeded {match_count} matches")

            # Train model
            logger.info("Training logistic regression model...")
            result = train_and_save_model(
                session,
                model_type="logistic",
                model_name="match_predictor",
                min_matches=30,  # Lower threshold for demo
            )

            if result["success"]:
                logger.info("✓ Model training completed successfully!")
                logger.info(f"  - Samples used: {result['samples_used']}")
                logger.info(f"  - Accuracy: {result['metrics']['accuracy']:.4f}")
                logger.info(f"  - Precision: {result['metrics']['precision']:.4f}")
                logger.info(f"  - Recall: {result['metrics']['recall']:.4f}")
                logger.info(f"  - F1 Score: {result['metrics']['f1']:.4f}")
                if result['metrics'].get('auc'):
                    logger.info(f"  - AUC Score: {result['metrics']['auc']:.4f}")
                logger.info(f"  - CV Mean: {result['metrics']['cv_mean']:.4f} (+/- {result['metrics']['cv_std']:.4f})")

                # Log model paths
                from src.ml.model import MODELS_DIR

                logger.info(f"\nModel files saved to: {MODELS_DIR}/")
                logger.info(f"  - {MODELS_DIR}/match_predictor.joblib")
                logger.info(f"  - {MODELS_DIR}/match_predictor_encoder.joblib")
                logger.info(f"  - {MODELS_DIR}/match_predictor_metadata.json")

                return True
            else:
                logger.error(f"✗ Model training failed: {result.get('error')}")
                return False

        finally:
            session.close()
            engine.dispose()

    except Exception as e:
        logger.error(f"✗ Error training model: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = train_baseline_model()
    sys.exit(0 if success else 1)
