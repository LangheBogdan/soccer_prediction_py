"""
Main FastAPI application for Soccer Prediction API.

Provides:
- RESTful API endpoints for match selection and prediction
- Database session management with dependency injection
- Comprehensive error handling and logging
- Request/response validation with Pydantic
- CORS middleware for frontend integration
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status, Depends, Query
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas import (
    LeagueResponse,
    TeamResponse,
    MatchResponse,
    MatchDetailResponse,
    MatchFilterQuery,
    ErrorResponse,
)
from src.api.routes import predictions, odds, ml
from src.db.models import League, Team, Match, MatchStatus

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ===== FastAPI Application Setup =====

app = FastAPI(
    title="Soccer Prediction API",
    description="Machine learning-based football match prediction system",
    version="0.1.0",
)

# ===== Middleware Setup =====

# CORS middleware for frontend integration
# In development, allow all origins; in production, specify allowed origins
if os.getenv("ENV", "development") == "development":
    allow_origins = ["*"]
else:
    allow_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)

# Trusted host middleware for security (only in production)
if os.getenv("ENV", "development") == "production":
    trusted_hosts = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1").split(",")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

# ===== Static Files Setup =====

# Mount static files (CSS, JavaScript, images)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ===== Frontend Routes =====

@app.get("/")
async def serve_frontend():
    """Serve the main HTML file."""
    html_path = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend not found"}
    )


@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon to prevent 404 errors."""
    return Response(status_code=204)


# ===== Include Route Routers =====

app.include_router(predictions.router)
app.include_router(odds.router)
app.include_router(ml.router)


# ===== CORS Preflight Handler (after routers) =====

@app.options("/{full_path:path}", include_in_schema=False)
async def preflight_handler(full_path: str):
    """Handle CORS preflight requests (OPTIONS) for all paths."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "http://localhost:8000",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )


# ===== Custom Exception Handlers =====

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with standard error response."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions with logging."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ===== Health Check Endpoints =====

@app.get("/", tags=["Health"])
def read_root():
    """Root endpoint - health check."""
    return {
        "message": "Soccer Prediction API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with database connectivity test."""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )


# ===== League Endpoints =====

@app.get("/api/leagues", response_model=list[LeagueResponse], tags=["Leagues"])
def get_leagues(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get all leagues.

    Query Parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 100, max: 100)

    Returns:
        List of league objects
    """
    try:
        limit = min(limit, 100)  # Cap at 100
        leagues = db.query(League).offset(skip).limit(limit).all()
        logger.info(f"Retrieved {len(leagues)} leagues")
        return leagues
    except Exception as e:
        logger.error(f"Failed to get leagues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leagues",
        )


@app.get("/api/leagues/{league_id}", response_model=LeagueResponse, tags=["Leagues"])
def get_league(league_id: int, db: Session = Depends(get_db)):
    """
    Get a specific league by ID.

    Path Parameters:
    - league_id: League ID

    Returns:
        League object

    Raises:
        HTTPException: If league not found
    """
    try:
        league = db.query(League).filter(League.id == league_id).first()
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League {league_id} not found",
            )
        return league
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get league {league_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league",
        )


# ===== Team Endpoints =====

@app.get("/api/leagues/{league_id}/teams", response_model=list[TeamResponse], tags=["Teams"])
def get_league_teams(
    league_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get all teams in a specific league.

    Path Parameters:
    - league_id: League ID

    Query Parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 100, max: 100)

    Returns:
        List of team objects
    """
    try:
        # Verify league exists
        league = db.query(League).filter(League.id == league_id).first()
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League {league_id} not found",
            )

        limit = min(limit, 100)
        teams = (
            db.query(Team)
            .filter(Team.league_id == league_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
        logger.info(f"Retrieved {len(teams)} teams for league {league_id}")
        return teams
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get teams for league {league_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve teams",
        )


# ===== Match Endpoints =====

@app.get("/api/matches", response_model=list[MatchResponse], tags=["Matches"])
def get_matches(
    league_id: Optional[int] = None,
    match_status: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get matches with optional filtering.

    Query Parameters:
    - league_id: Filter by league ID (optional)
    - match_status: Filter by match status: scheduled, live, finished, postponed, cancelled (optional)
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 50, max: 100)

    Returns:
        List of match objects
    """
    try:
        limit = min(limit, 100)
        query = db.query(Match)

        if league_id:
            query = query.filter(Match.league_id == league_id)

        if match_status:
            try:
                status_enum = MatchStatus[match_status.upper()]
                query = query.filter(Match.status == status_enum)
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {match_status}",
                )

        matches = query.offset(skip).limit(limit).all()
        logger.info(f"Retrieved {len(matches)} matches")
        return matches
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get matches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve matches",
        )


@app.get("/api/matches/{match_id}", response_model=MatchDetailResponse, tags=["Matches"])
def get_match_detail(match_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific match.

    Path Parameters:
    - match_id: Match ID

    Returns:
        Detailed match object with team and league information

    Raises:
        HTTPException: If match not found
    """
    try:
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match {match_id} not found",
            )
        return match
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get match {match_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve match",
        )


@app.get("/api/leagues/{league_id}/matches", response_model=list[MatchResponse], tags=["Matches"])
def get_league_matches(
    league_id: int,
    match_status: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get all matches in a specific league.

    Path Parameters:
    - league_id: League ID

    Query Parameters:
    - match_status: Filter by match status (optional)
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 50, max: 100)

    Returns:
        List of match objects for the league
    """
    try:
        # Verify league exists
        league = db.query(League).filter(League.id == league_id).first()
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League {league_id} not found",
            )

        limit = min(limit, 100)
        query = db.query(Match).filter(Match.league_id == league_id)

        if match_status:
            try:
                status_enum = MatchStatus[match_status.upper()]
                query = query.filter(Match.status == status_enum)
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {match_status}",
                )

        matches = query.offset(skip).limit(limit).all()
        logger.info(f"Retrieved {len(matches)} matches for league {league_id}")
        return matches
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get matches for league {league_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve matches",
        )


# ===== API Version Info =====

@app.get("/api/version", tags=["Info"])
def get_version():
    """Get API version and build information."""
    return {
        "version": "0.1.0",
        "api_version": "v1",
        "build_date": os.getenv("BUILD_DATE", "unknown"),
        "environment": os.getenv("ENV", "development"),
    }


# ===== Startup and Shutdown Events =====

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Soccer Prediction API")
    logger.info(f"Environment: {os.getenv('ENV', 'development')}")
    logger.info(f"Log level: {os.getenv('LOG_LEVEL', 'INFO')}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Soccer Prediction API")


# ===== Main Entry Point =====

def main():
    """Run the application."""
    import uvicorn

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", 8000))
    reload = os.getenv("ENV", "development") == "development"

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
