"""
Prediction-related API endpoints.

Provides endpoints for:
- Creating and retrieving predictions
- Viewing prediction history
- Getting user prediction statistics
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas import PredictionResponse, PredictionCreate, UserStatsResponse
from src.db.models import Prediction, PredictionResult, User, Match

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.post("", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
def create_prediction(
    prediction: PredictionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new prediction for a match.

    Request Body:
    - user_id: User ID making the prediction
    - match_id: Match ID to predict for
    - predicted_outcome: Prediction outcome (home_win, draw, away_win)
    - confidence: Prediction confidence (0.0 to 1.0)
    - stake: Betting stake (optional)
    - odds_used: Odds at prediction time (optional)
    - notes: Additional notes (optional)

    Returns:
        Created prediction object

    Raises:
        HTTPException: If user or match not found, or validation fails
    """
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == prediction.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {prediction.user_id} not found",
            )

        # Verify match exists
        match = db.query(Match).filter(Match.id == prediction.match_id).first()
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match {prediction.match_id} not found",
            )

        # Create prediction
        new_prediction = Prediction(
            user_id=prediction.user_id,
            match_id=prediction.match_id,
            predicted_outcome=prediction.predicted_outcome,
            confidence=prediction.confidence,
            stake=prediction.stake,
            odds_used=prediction.odds_used,
            notes=prediction.notes,
        )

        db.add(new_prediction)
        db.commit()
        db.refresh(new_prediction)

        logger.info(f"Created prediction {new_prediction.id} for user {prediction.user_id}")
        return new_prediction

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create prediction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create prediction",
        )


@router.get("/{prediction_id}", response_model=PredictionResponse)
def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific prediction by ID.

    Path Parameters:
    - prediction_id: Prediction ID

    Returns:
        Prediction object

    Raises:
        HTTPException: If prediction not found
    """
    try:
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prediction {prediction_id} not found",
            )
        return prediction
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prediction {prediction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve prediction",
        )


@router.get("/user/{user_id}", response_model=list[PredictionResponse])
def get_user_predictions(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get all predictions for a specific user.

    Path Parameters:
    - user_id: User ID

    Query Parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 50, max: 100)

    Returns:
        List of prediction objects

    Raises:
        HTTPException: If user not found
    """
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        limit = min(limit, 100)
        predictions = (
            db.query(Prediction)
            .filter(Prediction.user_id == user_id)
            .order_by(Prediction.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        logger.info(f"Retrieved {len(predictions)} predictions for user {user_id}")
        return predictions

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get predictions for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve predictions",
        )


@router.get("/user/{user_id}/stats", response_model=UserStatsResponse)
def get_user_stats(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Get prediction statistics for a specific user.

    Path Parameters:
    - user_id: User ID

    Returns:
        User statistics including accuracy, ROI, etc.

    Raises:
        HTTPException: If user not found or stats cannot be calculated
    """
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        # Get all predictions for user
        predictions = (
            db.query(Prediction)
            .filter(Prediction.user_id == user_id)
            .all()
        )

        total_predictions = len(predictions)

        if total_predictions == 0:
            return UserStatsResponse(
                total_predictions=0,
                correct_predictions=0,
                accuracy=0.0,
                total_stake=None,
                total_profit_loss=None,
                average_confidence=0.0,
                roi=None,
            )

        # Calculate statistics
        correct_predictions = 0
        total_stake = 0
        total_profit_loss = 0
        total_confidence = 0

        for prediction in predictions:
            total_confidence += prediction.confidence

            if prediction.result:
                if prediction.result.is_correct:
                    correct_predictions += 1
                if prediction.stake:
                    total_stake += float(prediction.stake)
                if prediction.result.profit_loss:
                    total_profit_loss += float(prediction.result.profit_loss)

        accuracy = (correct_predictions / total_predictions) if total_predictions > 0 else 0
        average_confidence = total_confidence / total_predictions
        roi = ((total_profit_loss / total_stake) * 100) if total_stake > 0 else None

        return UserStatsResponse(
            total_predictions=total_predictions,
            correct_predictions=correct_predictions,
            accuracy=accuracy,
            total_stake=total_stake if total_stake > 0 else None,
            total_profit_loss=total_profit_loss if total_profit_loss > 0 else None,
            average_confidence=average_confidence,
            roi=roi,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate user statistics",
        )
