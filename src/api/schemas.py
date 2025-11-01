"""
Pydantic request/response schemas for API endpoints.

Defines data validation and serialization for API communication.
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field


# ===== League Schemas =====

class LeagueBase(BaseModel):
    """Base league schema."""
    name: str = Field(..., min_length=1, max_length=255)
    country: str = Field(..., min_length=1, max_length=100)
    season: str = Field(..., pattern=r"^\d{4}-\d{2}$")  # e.g., 2023-24
    league_type: str = Field(default="domestic")
    external_id: Optional[str] = None


class LeagueCreate(LeagueBase):
    """Schema for creating a league."""
    pass


class LeagueResponse(LeagueBase):
    """Schema for league response."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Team Schemas =====

class TeamBase(BaseModel):
    """Base team schema."""
    name: str = Field(..., min_length=1, max_length=255)
    country: str = Field(..., min_length=1, max_length=100)
    league_id: int
    founded_year: Optional[int] = None
    external_id: Optional[str] = None


class TeamCreate(TeamBase):
    """Schema for creating a team."""
    pass


class TeamResponse(TeamBase):
    """Schema for team response."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Match Schemas =====

class MatchBase(BaseModel):
    """Base match schema."""
    league_id: int
    home_team_id: int
    away_team_id: int
    match_date: datetime
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    status: str = "scheduled"


class MatchCreate(MatchBase):
    """Schema for creating a match."""
    pass


class MatchUpdate(BaseModel):
    """Schema for updating a match."""
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    status: Optional[str] = None


class MatchResponse(MatchBase):
    """Schema for match response."""
    id: int
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_shots_on_target: Optional[int] = None
    away_shots_on_target: Optional[int] = None
    home_possession: Optional[float] = None
    away_possession: Optional[float] = None
    home_passes: Optional[int] = None
    away_passes: Optional[int] = None
    home_pass_accuracy: Optional[float] = None
    away_pass_accuracy: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MatchDetailResponse(MatchResponse):
    """Detailed match response with team info."""
    home_team: TeamResponse
    away_team: TeamResponse
    league: LeagueResponse


# ===== Odds Schemas =====

class OddsBase(BaseModel):
    """Base odds schema."""
    match_id: int
    bookmaker: str = Field(..., min_length=1, max_length=100)
    home_win_odds: Decimal = Field(..., gt=0)
    draw_odds: Decimal = Field(..., gt=0)
    away_win_odds: Decimal = Field(..., gt=0)
    retrieved_at: datetime


class OddsCreate(OddsBase):
    """Schema for creating odds."""
    over_2_5_odds: Optional[Decimal] = None
    under_2_5_odds: Optional[Decimal] = None


class OddsResponse(OddsBase):
    """Schema for odds response."""
    id: int
    over_2_5_odds: Optional[Decimal] = None
    under_2_5_odds: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Prediction Schemas =====

class PredictionBase(BaseModel):
    """Base prediction schema."""
    user_id: int
    match_id: int
    predicted_outcome: str = Field(..., pattern="^(home_win|draw|away_win)$")
    confidence: float = Field(..., ge=0.0, le=1.0)


class PredictionCreate(PredictionBase):
    """Schema for creating a prediction."""
    stake: Optional[Decimal] = None
    odds_used: Optional[Decimal] = None
    notes: Optional[str] = None


class PredictionResponse(PredictionBase):
    """Schema for prediction response."""
    id: int
    stake: Optional[Decimal] = None
    odds_used: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Prediction Result Schemas =====

class PredictionResultResponse(BaseModel):
    """Schema for prediction result response."""
    id: int
    prediction_id: int
    actual_outcome: str
    is_correct: bool
    profit_loss: Optional[Decimal] = None
    return_rate: Optional[float] = None
    evaluated_at: datetime

    class Config:
        from_attributes = True


class PredictionResult(BaseModel):
    """Schema for ML model prediction result."""
    match_id: int
    predicted_outcome: str = Field(..., pattern="^(home_win|draw|away_win)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    probabilities: dict = Field(..., description="Probabilities for each outcome")


# ===== Error Schemas =====

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    status_code: int
    timestamp: datetime


# ===== Query Schemas =====

class MatchFilterQuery(BaseModel):
    """Query parameters for filtering matches."""
    league_id: Optional[int] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PredictionHistoryQuery(BaseModel):
    """Query parameters for prediction history."""
    user_id: int
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    status: Optional[str] = None  # all, correct, incorrect


# ===== Statistics Schemas =====

class UserStatsResponse(BaseModel):
    """Schema for user prediction statistics."""
    total_predictions: int
    correct_predictions: int
    accuracy: float
    total_stake: Optional[Decimal] = None
    total_profit_loss: Optional[Decimal] = None
    average_confidence: float
    roi: Optional[float] = None


class LeagueStatsResponse(BaseModel):
    """Schema for league statistics."""
    league_id: int
    league_name: str
    total_matches: int
    completed_matches: int
    scheduled_matches: int
    teams_count: int


# ===== Bulk Operation Schemas =====

class BulkCreateMatchesRequest(BaseModel):
    """Schema for bulk creating matches."""
    league_id: int
    matches: List[MatchBase]


class BulkCreateMatchesResponse(BaseModel):
    """Response for bulk match creation."""
    created_count: int
    failed_count: int
    errors: List[dict] = []
