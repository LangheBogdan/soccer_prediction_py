"""
Betting odds-related API endpoints.

Provides endpoints for:
- Retrieving betting odds for matches
- Getting best odds across bookmakers
- Historical odds tracking
- Fetching live odds from external API
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas import OddsResponse
from src.db.models import Odds, Match, League
from src.scraper.pipeline import DataPipeline

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/odds", tags=["Odds"])


@router.get("/match/{match_id}", response_model=list[OddsResponse])
def get_match_odds(
    match_id: int,
    bookmaker: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get betting odds for a specific match.

    Path Parameters:
    - match_id: Match ID

    Query Parameters:
    - bookmaker: Filter by specific bookmaker (optional)

    Returns:
        List of odds from different bookmakers for the match

    Raises:
        HTTPException: If match not found
    """
    try:
        # Verify match exists
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match {match_id} not found",
            )

        # Get odds for match
        query = db.query(Odds).filter(Odds.match_id == match_id)

        if bookmaker:
            query = query.filter(Odds.bookmaker == bookmaker)

        odds_list = query.order_by(Odds.retrieved_at.desc()).all()

        logger.info(f"Retrieved {len(odds_list)} odds for match {match_id}")
        return odds_list

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get odds for match {match_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve odds",
        )


@router.get("/match/{match_id}/best", response_model=dict)
def get_best_odds(
    match_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the best odds across all bookmakers for a match.

    Path Parameters:
    - match_id: Match ID

    Returns:
        Dictionary with best odds for each outcome (home_win, draw, away_win)
        and the corresponding bookmaker

    Raises:
        HTTPException: If match not found or no odds available
    """
    try:
        # Verify match exists
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match {match_id} not found",
            )

        # Get all odds for match
        odds_list = (
            db.query(Odds)
            .filter(Odds.match_id == match_id)
            .order_by(Odds.retrieved_at.desc())
            .all()
        )

        if not odds_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No odds available for match {match_id}",
            )

        # Find best odds for each outcome
        best_home_win = None
        best_home_win_bm = None
        best_draw = None
        best_draw_bm = None
        best_away_win = None
        best_away_win_bm = None

        for odds in odds_list:
            if best_home_win is None or odds.home_win_odds > best_home_win:
                best_home_win = odds.home_win_odds
                best_home_win_bm = odds.bookmaker

            if best_draw is None or odds.draw_odds > best_draw:
                best_draw = odds.draw_odds
                best_draw_bm = odds.bookmaker

            if best_away_win is None or odds.away_win_odds > best_away_win:
                best_away_win = odds.away_win_odds
                best_away_win_bm = odds.bookmaker

        return {
            "match_id": match_id,
            "home_win": {
                "odds": float(best_home_win),
                "bookmaker": best_home_win_bm,
            },
            "draw": {
                "odds": float(best_draw),
                "bookmaker": best_draw_bm,
            },
            "away_win": {
                "odds": float(best_away_win),
                "bookmaker": best_away_win_bm,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get best odds for match {match_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate best odds",
        )


@router.get("/bookmakers", response_model=list[str])
def get_available_bookmakers(db: Session = Depends(get_db)):
    """
    Get list of available bookmakers with odds in the system.

    Returns:
        List of unique bookmaker names

    Raises:
        HTTPException: If query fails
    """
    try:
        # Get unique bookmakers from database
        bookmakers = (
            db.query(Odds.bookmaker)
            .distinct()
            .order_by(Odds.bookmaker)
            .all()
        )

        bookmaker_list = [bm[0] for bm in bookmakers]
        logger.info(f"Retrieved {len(bookmaker_list)} available bookmakers")
        return bookmaker_list

    except Exception as e:
        logger.error(f"Failed to get available bookmakers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bookmakers",
        )


@router.get("/match/{match_id}/comparison", response_model=dict)
def compare_odds(
    match_id: int,
    db: Session = Depends(get_db),
):
    """
    Compare odds across all bookmakers for a match in a tabular format.

    Path Parameters:
    - match_id: Match ID

    Returns:
        Dictionary with odds from each bookmaker in comparison format

    Raises:
        HTTPException: If match not found
    """
    try:
        # Verify match exists
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match {match_id} not found",
            )

        # Get all odds for match
        odds_list = (
            db.query(Odds)
            .filter(Odds.match_id == match_id)
            .order_by(Odds.retrieved_at.desc())
            .all()
        )

        if not odds_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No odds available for match {match_id}",
            )

        # Build comparison table
        comparison = {
            "match_id": match_id,
            "bookmakers": {},
        }

        for odds in odds_list:
            comparison["bookmakers"][odds.bookmaker] = {
                "home_win": float(odds.home_win_odds),
                "draw": float(odds.draw_odds),
                "away_win": float(odds.away_win_odds),
                "over_2_5": float(odds.over_2_5_odds) if odds.over_2_5_odds else None,
                "under_2_5": float(odds.under_2_5_odds) if odds.under_2_5_odds else None,
                "retrieved_at": odds.retrieved_at.isoformat(),
            }

        logger.info(f"Generated odds comparison for match {match_id}")
        return comparison

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare odds for match {match_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate odds comparison",
        )


@router.post("/match/{match_id}/fetch", response_model=dict)
def fetch_live_odds_for_match(
    match_id: int,
    db: Session = Depends(get_db),
):
    """
    Fetch live odds for a specific match from the Odds API.

    This endpoint fetches fresh odds from the-odds-api.com and stores them in the database.

    Path Parameters:
    - match_id: Match ID

    Returns:
        Dictionary with fetch results and stored odds count

    Raises:
        HTTPException: If match not found or API key not configured
    """
    try:
        # Verify match exists
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match {match_id} not found",
            )

        # Get league for the match
        league = db.query(League).filter(League.id == match.league_id).first()
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League not found for match {match_id}",
            )

        # Get API key from environment
        odds_api_key = os.getenv('ODDS_API_KEY')
        if not odds_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Odds API not configured. Please set ODDS_API_KEY environment variable.",
            )

        # Initialize pipeline with odds API
        pipeline = DataPipeline(
            db_session=db,
            odds_api_key=odds_api_key,
        )

        # Fetch and store odds
        logger.info(f"Fetching live odds for match {match_id}")
        result = pipeline.fetch_and_store_odds(
            league_code=league.name,  # Assuming league.name contains code like 'EPL'
            match_id=match_id,
        )

        return {
            "match_id": match_id,
            "odds_fetched": result['odds_fetched'],
            "odds_stored": result['odds_stored'],
            "errors": result['errors'],
            "success": result['odds_stored'] > 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch live odds for match {match_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch live odds: {str(e)}",
        )


@router.post("/league/{league_id}/fetch", response_model=dict)
def fetch_live_odds_for_league(
    league_id: int,
    db: Session = Depends(get_db),
):
    """
    Fetch live odds for all matches in a league from the Odds API.

    This endpoint fetches fresh odds for all upcoming matches in a league.

    Path Parameters:
    - league_id: League ID

    Returns:
        Dictionary with fetch results and stored odds count

    Raises:
        HTTPException: If league not found or API key not configured
    """
    try:
        # Verify league exists
        league = db.query(League).filter(League.id == league_id).first()
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League {league_id} not found",
            )

        # Get API key from environment
        odds_api_key = os.getenv('ODDS_API_KEY')
        if not odds_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Odds API not configured. Please set ODDS_API_KEY environment variable.",
            )

        # Initialize pipeline with odds API
        pipeline = DataPipeline(
            db_session=db,
            odds_api_key=odds_api_key,
        )

        # Fetch and store odds for all league matches
        logger.info(f"Fetching live odds for league {league_id}")
        result = pipeline.fetch_and_store_odds(
            league_code=league.name,
        )

        return {
            "league_id": league_id,
            "odds_fetched": result['odds_fetched'],
            "odds_stored": result['odds_stored'],
            "errors": result['errors'],
            "success": result['odds_stored'] > 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch live odds for league {league_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch live odds: {str(e)}",
        )
