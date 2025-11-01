"""
ML model training, evaluation, and prediction for match outcomes.

This module provides functions to train, evaluate, and use ML models
for predicting football match outcomes (home win, draw, away win).
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sqlalchemy.orm import Session

from src.db.models import PredictionOutcome, ModelMetrics
from src.ml.features import create_training_dataset, extract_match_features, get_feature_names

logger = logging.getLogger(__name__)

# Default model directory
MODELS_DIR = Path(__file__).parent.parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


class ModelManager:
    """Manager for ML model training, saving, and loading."""

    def __init__(self, model_name: str = "match_predictor"):
        """
        Initialize model manager.

        Args:
            model_name: Name of the model (used for file paths)
        """
        self.model_name = model_name
        self.model_path = MODELS_DIR / f"{model_name}.joblib"
        self.encoder_path = MODELS_DIR / f"{model_name}_encoder.joblib"
        self.metadata_path = MODELS_DIR / f"{model_name}_metadata.json"
        self.model = None
        self.label_encoder = None
        self.feature_names = get_feature_names()

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_type: str = "logistic",
        test_size: float = 0.2,
        random_state: int = 42,
        **model_kwargs
    ) -> Dict[str, float]:
        """
        Train an ML model on the provided dataset.

        Args:
            X: Feature DataFrame
            y: Target Series (outcome labels)
            model_type: Type of model ("logistic" or "random_forest")
            test_size: Proportion of data to use for testing
            random_state: Random seed for reproducibility
            **model_kwargs: Additional keyword arguments for model initialization

        Returns:
            Dictionary with evaluation metrics
        """
        # Encode target labels
        self.label_encoder = LabelEncoder()
        y_encoded = self.label_encoder.fit_transform(y)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=test_size, random_state=random_state, stratify=y_encoded
        )

        logger.info(
            f"Training {model_type} model with {len(X_train)} training samples "
            f"and {len(X_test)} test samples"
        )

        # Create model
        if model_type == "logistic":
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=random_state,
                multi_class="multinomial",
                **model_kwargs
            )
        elif model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100,
                random_state=random_state,
                n_jobs=-1,
                **model_kwargs
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Train model
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)

        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, average="weighted"),
            "recall": recall_score(y_test, y_pred, average="weighted"),
            "f1": f1_score(y_test, y_pred, average="weighted"),
        }

        # Calculate AUC for binary classification (one-vs-rest)
        try:
            metrics["auc"] = roc_auc_score(y_test, y_pred_proba, multi_class="ovr", average="weighted")
        except Exception as e:
            logger.warning(f"Could not calculate AUC: {e}")
            metrics["auc"] = None

        # Cross-validation score
        cv_scores = cross_val_score(
            self.model, X_train, y_train, cv=5, scoring="accuracy"
        )
        metrics["cv_mean"] = cv_scores.mean()
        metrics["cv_std"] = cv_scores.std()

        logger.info(f"Model evaluation metrics: {metrics}")

        return metrics

    def save(self, session: Session, model_type: str = "logistic") -> None:
        """
        Save trained model and metadata to disk.

        Args:
            session: SQLAlchemy session for storing metrics
            model_type: Type of model trained
        """
        if self.model is None:
            raise ValueError("Model has not been trained yet")

        # Save model and encoder
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.label_encoder, self.encoder_path)

        logger.info(f"Saved model to {self.model_path}")

        # Save metadata
        metadata = {
            "model_name": self.model_name,
            "model_type": model_type,
            "saved_at": datetime.utcnow().isoformat(),
            "feature_names": self.feature_names,
            "classes": self.label_encoder.classes_.tolist() if self.label_encoder else [],
        }

        with open(self.metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved metadata to {self.metadata_path}")

    def load(self) -> bool:
        """
        Load trained model from disk.

        Returns:
            True if model loaded successfully, False otherwise
        """
        if not self.model_path.exists() or not self.encoder_path.exists():
            logger.warning(f"Model files not found at {self.model_path}")
            return False

        self.model = joblib.load(self.model_path)
        self.label_encoder = joblib.load(self.encoder_path)

        logger.info(f"Loaded model from {self.model_path}")
        return True

    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions on new data.

        Args:
            X: Feature DataFrame

        Returns:
            Tuple of (predictions, probabilities)
        """
        if self.model is None:
            raise ValueError("Model has not been trained or loaded")

        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)

        # Decode predictions back to outcome labels
        decoded_predictions = self.label_encoder.inverse_transform(predictions)

        return decoded_predictions, probabilities


def train_and_save_model(
    session: Session,
    model_type: str = "logistic",
    model_name: str = "match_predictor",
    min_matches: int = 500,
) -> Dict[str, any]:
    """
    Train and save a new model.

    Args:
        session: SQLAlchemy session
        model_type: Type of model to train
        model_name: Name of the model
        min_matches: Minimum number of matches required for training

    Returns:
        Dictionary with training results and metrics
    """
    logger.info(f"Starting model training with model_type={model_type}")

    try:
        # Create training dataset
        X, y = create_training_dataset(session, min_matches=min_matches)

        # Train model
        manager = ModelManager(model_name)
        metrics = manager.train(X, y, model_type=model_type)

        # Save model
        manager.save(session, model_type)

        # Store metrics in database
        db_metrics = ModelMetrics(
            model_version=f"{model_name}_v1",
            training_date=datetime.utcnow(),
            accuracy=metrics["accuracy"],
            precision=metrics["precision"],
            recall=metrics["recall"],
            f1_score=metrics["f1"],
            auc_score=metrics.get("auc"),
            samples_used=len(X),
        )
        session.add(db_metrics)
        session.commit()

        logger.info("Model training completed successfully")

        return {
            "success": True,
            "model_name": model_name,
            "model_type": model_type,
            "metrics": metrics,
            "samples_used": len(X),
        }

    except Exception as e:
        logger.error(f"Model training failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def get_prediction_for_match(
    session: Session, match_object, model_name: str = "match_predictor"
) -> Optional[Dict[str, any]]:
    """
    Get ML prediction for a specific match.

    Args:
        session: SQLAlchemy session
        match_object: Match ORM object
        model_name: Name of the model to use

    Returns:
        Dictionary with prediction details or None if prediction fails
    """
    try:
        # Load model
        manager = ModelManager(model_name)
        if not manager.load():
            logger.error("Failed to load model")
            return None

        # Extract features for the match
        features_dict = extract_match_features(session, match_object)
        features_df = pd.DataFrame([features_dict])

        # Make prediction
        predictions, probabilities = manager.predict(features_df)

        # Get prediction details
        predicted_outcome = predictions[0]
        class_indices = {
            cls: idx for idx, cls in enumerate(manager.label_encoder.classes_)
        }
        outcome_idx = class_indices.get(predicted_outcome, 0)
        confidence = float(probabilities[0, outcome_idx])

        return {
            "match_id": match_object.id,
            "predicted_outcome": predicted_outcome,
            "confidence": confidence,
            "probabilities": {
                outcome: float(prob)
                for outcome, prob in zip(
                    manager.label_encoder.classes_, probabilities[0]
                )
            },
        }

    except Exception as e:
        logger.error(f"Prediction failed for match {match_object.id}: {e}", exc_info=True)
        return None


def get_model_metrics(session: Session, limit: int = 10) -> list[Dict[str, any]]:
    """
    Get recent model metrics from database.

    Args:
        session: SQLAlchemy session
        limit: Maximum number of metrics to retrieve

    Returns:
        List of model metrics dictionaries
    """
    metrics = (
        session.query(ModelMetrics)
        .order_by(ModelMetrics.training_date.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "model_version": m.model_version,
            "training_date": m.training_date.isoformat(),
            "accuracy": float(m.accuracy),
            "precision": float(m.precision),
            "recall": float(m.recall),
            "f1_score": float(m.f1_score),
            "auc_score": float(m.auc_score) if m.auc_score else None,
            "samples_used": m.samples_used,
        }
        for m in metrics
    ]
