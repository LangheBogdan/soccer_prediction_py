"""
Client for api-football.com API.

This module provides functionality to fetch match details, player statistics,
and team information from the api-football.com API (RapidAPI).

API Documentation: https://rapidapi.com/api-sports/api/api-football
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import requests

# Configure logging
logger = logging.getLogger(__name__)


class ApiFootballError(Exception):
    """Base exception for api-football.com API errors."""
    pass


class RateLimitError(ApiFootballError):
    """Raised when API rate limit is exceeded."""
    pass


class ApiFootballClient:
    """
    Client for api-football.com API (RapidAPI).

    Attributes:
        api_key (str): RapidAPI key for api-football
        api_host (str): RapidAPI host header
        base_url (str): Base URL for API endpoints
    """

    BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"
    RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"

    # League IDs in api-football
    LEAGUE_IDS = {
        'EPL': 39,
        'LA_LIGA': 140,
        'SERIE_A': 135,
        'BUNDESLIGA': 78,
        'LIGUE_1': 61,
        'EREDIVISIE': 88,
        'LIGA_NOS': 94,
    }

    def __init__(self, api_key: str, request_delay: float = 0.25):
        """
        Initialize the api-football.com client.

        Args:
            api_key: RapidAPI key for api-football
            request_delay: Delay between requests in seconds

        Raises:
            ValueError: If API key is empty
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        self.api_key = api_key
        self.request_delay = request_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': self.RAPIDAPI_HOST,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _rate_limit_check(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            delay = self.request_delay - elapsed
            time.sleep(delay)
        self.last_request_time = time.time()

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a GET request to the API.

        Args:
            endpoint: API endpoint (e.g., '/fixtures')
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            ApiFootballError: If request fails
            RateLimitError: If rate limit is exceeded
        """
        self._rate_limit_check()
        url = f"{self.BASE_URL}{endpoint}"

        try:
            logger.debug(f"GET {url}")
            response = self.session.get(url, params=params, timeout=10)

            # Check for rate limiting
            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")

            if response.status_code == 400:
                logger.error(f"Bad request: {response.json()}")
                raise ApiFootballError(f"Bad request: {response.text}")

            response.raise_for_status()
            data = response.json()

            # Check API-level errors
            if data.get('errors'):
                errors = data.get('errors', {})
                logger.error(f"API errors: {errors}")
                raise ApiFootballError(f"API error: {errors}")

            return data

        except requests.Timeout:
            logger.error(f"Timeout: {url}")
            raise ApiFootballError(f"Request timeout: {url}")
        except requests.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            raise ApiFootballError(f"Request error: {e}")

    def get_fixtures(
        self,
        league_id: int,
        season: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get fixtures/matches for a league and season.

        Args:
            league_id: League ID (from LEAGUE_IDS)
            season: Season year (e.g., 2023)
            status: Match status ('SCHEDULED', 'LIVE', 'FINISHED', 'POSTPONED')

        Returns:
            List of fixture dictionaries

        Raises:
            ApiFootballError: If API request fails
        """
        try:
            params = {
                'league': league_id,
                'season': season
            }
            if status:
                params['status'] = status

            response = self._get('/fixtures', params=params)
            fixtures = response.get('response', [])
            logger.info(f"Retrieved {len(fixtures)} fixtures for league {league_id}")
            return fixtures

        except ApiFootballError as e:
            logger.error(f"Failed to get fixtures: {e}")
            raise

    def get_fixture_details(self, fixture_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific fixture/match.

        Args:
            fixture_id: Fixture ID from API

        Returns:
            Dictionary with fixture details

        Raises:
            ApiFootballError: If API request fails
        """
        try:
            response = self._get('/fixtures', params={'id': fixture_id})
            fixtures = response.get('response', [])

            if not fixtures:
                raise ApiFootballError(f"Fixture not found: {fixture_id}")

            logger.info(f"Retrieved details for fixture {fixture_id}")
            return fixtures[0]

        except ApiFootballError as e:
            logger.error(f"Failed to get fixture {fixture_id}: {e}")
            raise

    def get_league_standings(self, league_id: int, season: int) -> List[Dict[str, Any]]:
        """
        Get league standings/table.

        Args:
            league_id: League ID (from LEAGUE_IDS)
            season: Season year (e.g., 2023)

        Returns:
            List of team standings

        Raises:
            ApiFootballError: If API request fails
        """
        try:
            response = self._get(
                '/standings',
                params={'league': league_id, 'season': season}
            )

            standings = response.get('response', [])
            if standings and 'league' in standings[0]:
                table = standings[0]['league'].get('standings', [[]])[0]
                logger.info(f"Retrieved standings for league {league_id}")
                return table

            return []

        except ApiFootballError as e:
            logger.error(f"Failed to get standings for league {league_id}: {e}")
            raise

    def get_team_statistics(self, league_id: int, team_id: int, season: int) -> Dict[str, Any]:
        """
        Get team statistics for a season.

        Args:
            league_id: League ID
            team_id: Team ID
            season: Season year

        Returns:
            Dictionary with team statistics

        Raises:
            ApiFootballError: If API request fails
        """
        try:
            response = self._get(
                '/teams/statistics',
                params={'league': league_id, 'season': season, 'team': team_id}
            )

            stats = response.get('response', {})
            logger.info(f"Retrieved statistics for team {team_id}")
            return stats

        except ApiFootballError as e:
            logger.error(f"Failed to get team statistics: {e}")
            raise

    def get_player_statistics(
        self,
        player_id: int,
        league_id: int,
        season: int
    ) -> Dict[str, Any]:
        """
        Get player statistics for a season.

        Args:
            player_id: Player ID
            league_id: League ID
            season: Season year

        Returns:
            Dictionary with player statistics

        Raises:
            ApiFootballError: If API request fails
        """
        try:
            response = self._get(
                '/players/statistics',
                params={'id': player_id, 'league': league_id, 'season': season}
            )

            stats = response.get('response', {})
            logger.info(f"Retrieved statistics for player {player_id}")
            return stats

        except ApiFootballError as e:
            logger.error(f"Failed to get player statistics: {e}")
            raise

    def get_head_to_head(self, team_id_1: int, team_id_2: int) -> List[Dict[str, Any]]:
        """
        Get head-to-head match history between two teams.

        Args:
            team_id_1: First team ID
            team_id_2: Second team ID

        Returns:
            List of head-to-head fixtures

        Raises:
            ApiFootballError: If API request fails
        """
        try:
            response = self._get(
                '/fixtures/headtohead',
                params={'h2h': f'{team_id_1}-{team_id_2}', 'last': 10}
            )

            fixtures = response.get('response', [])
            logger.info(f"Retrieved {len(fixtures)} h2h matches for teams {team_id_1} vs {team_id_2}")
            return fixtures

        except ApiFootballError as e:
            logger.error(f"Failed to get h2h matches: {e}")
            raise

    def get_odds(self, fixture_id: int) -> Dict[str, Any]:
        """
        Get betting odds for a fixture.

        Args:
            fixture_id: Fixture ID

        Returns:
            Dictionary with odds information

        Raises:
            ApiFootballError: If API request fails
        """
        try:
            response = self._get('/odds', params={'fixture': fixture_id})
            odds = response.get('response', {})
            logger.info(f"Retrieved odds for fixture {fixture_id}")
            return odds

        except ApiFootballError as e:
            logger.error(f"Failed to get odds for fixture {fixture_id}: {e}")
            raise

    def get_fixtures_by_date(
        self,
        league_id: int,
        date_from: str,
        date_to: str
    ) -> List[Dict[str, Any]]:
        """
        Get fixtures for a league within a date range.

        Args:
            league_id: League ID
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            List of fixtures

        Raises:
            ApiFootballError: If API request fails
        """
        try:
            response = self._get(
                '/fixtures',
                params={
                    'league': league_id,
                    'from': date_from,
                    'to': date_to
                }
            )

            fixtures = response.get('response', [])
            logger.info(
                f"Retrieved {len(fixtures)} fixtures for league {league_id} "
                f"from {date_from} to {date_to}"
            )
            return fixtures

        except ApiFootballError as e:
            logger.error(f"Failed to get fixtures by date: {e}")
            raise

    def get_injuries(self, league_id: int, season: int) -> List[Dict[str, Any]]:
        """
        Get player injuries for a league.

        Args:
            league_id: League ID
            season: Season year

        Returns:
            List of injury information

        Raises:
            ApiFootballError: If API request fails
        """
        try:
            response = self._get(
                '/injuries',
                params={'league': league_id, 'season': season}
            )

            injuries = response.get('response', [])
            logger.info(f"Retrieved {len(injuries)} injuries for league {league_id}")
            return injuries

        except ApiFootballError as e:
            logger.error(f"Failed to get injuries: {e}")
            raise
