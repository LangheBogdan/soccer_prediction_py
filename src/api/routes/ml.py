"""
ML model endpoints for match predictions and model management.

Provides endpoints for:
- GET ML prediction for a match
- Get model performance metrics
- Trigger model retraining
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas import (
    PredictionResult,
    ErrorResponse,
)
from src.db.models import Match, MatchStatus, ModelMetrics
from src.ml.model import get_prediction_for_match, train_and_save_model, get_model_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.post(
    "/predict/match/{match_id}",
    response_model=PredictionResult,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Match not found"},
        400: {"model": ErrorResponse, "description": "Match not finished or match status invalid for prediction"},
        503: {"model": ErrorResponse, "description": "ML model unavailable or prediction failed"},
    },
)
def predict_match(
    match_id: int,
    db: Session = Depends(get_db),
) -> PredictionResult:
    """
    Generate ML prediction for a match.

    Args:
        match_id: ID of the match to predict
        db: Database session (injected)

    Returns:
        PredictionResult with predicted outcome and confidence

    Raises:
        404: If match not found
        400: If match status is not appropriate for prediction
        503: If ML model is unavailable or prediction fails
    """
    # Get match
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match {match_id} not found",
        )

    # Only allow predictions for scheduled/live matches
    if match.status not in [MatchStatus.SCHEDULED, MatchStatus.LIVE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot predict match with status '{match.status.value}'. "
                   f"Only scheduled or live matches can be predicted.",
        )

    # Get prediction from model
    prediction = get_prediction_for_match(db, match)
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model unavailable or prediction failed",
        )

    return PredictionResult(
        match_id=prediction["match_id"],
        predicted_outcome=prediction["predicted_outcome"],
        confidence=prediction["confidence"],
        probabilities=prediction["probabilities"],
    )


@router.get(
    "/model/metrics",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    responses={
        503: {"model": ErrorResponse, "description": "No trained models found"},
    },
)
def get_ml_metrics(
    db: Session = Depends(get_db),
    limit: int = 10,
) -> list[dict]:
    """
    Get ML model performance metrics.

    Args:
        db: Database session (injected)
        limit: Maximum number of metrics to retrieve

    Returns:
        List of model metrics from recent trainings

    Raises:
        503: If no trained models found
    """
    metrics = get_model_metrics(db, limit=limit)

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No trained models found",
        )

    return metrics


@router.post(
    "/model/train",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    responses={
        503: {"model": ErrorResponse, "description": "Training failed or insufficient data"},
    },
)
def train_model(
    db: Session = Depends(get_db),
    model_type: str = "logistic",
    min_matches: int = 500,
) -> dict:
    """
    Trigger ML model retraining with latest data.

    Args:
        db: Database session (injected)
        model_type: Type of model to train ("logistic" or "random_forest")
        min_matches: Minimum number of finished matches required

    Returns:
        Training result with metrics and status

    Raises:
        503: If training fails or insufficient data
    """
    # Validate model type
    if model_type not in ["logistic", "random_forest"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model_type '{model_type}'. Must be 'logistic' or 'random_forest'.",
        )

    logger.info(f"Starting model training with type={model_type}")

    # Train model
    result = train_and_save_model(
        db,
        model_type=model_type,
        model_name="match_predictor",
        min_matches=min_matches,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model training failed: {result.get('error', 'Unknown error')}",
        )

    return {
        "status": "success",
        "model_name": result["model_name"],
        "model_type": result["model_type"],
        "samples_used": result["samples_used"],
        "metrics": result["metrics"],
    }
