"""
Client for football-data.org API.

This module provides functionality to fetch current matches, standings,
and betting odds from the football-data.org API.

API Documentation: https://www.football-data.org/client/register
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import requests

# Configure logging
logger = logging.getLogger(__name__)


class FootballDataError(Exception):
    """Base exception for football-data.org API errors."""
    pass


class RateLimitError(FootballDataError):
    """Raised when API rate limit is exceeded."""
    pass


class FootballDataClient:
    """
    Client for football-data.org API.

    Attributes:
        api_key (str): API key for football-data.org
        base_url (str): Base URL for API endpoints
    """

    BASE_URL = "https://api.football-data.org/v4"

    # League codes mapping
    LEAGUE_CODES = {
        'EPL': 'PL',
        'LA_LIGA': 'SA',
        'SERIE_A': 'SA',
        'BUNDESLIGA': 'BL1',
        'LIGUE_1': 'FL1',
        'EREDIVISIE': 'DED',
        'LIGA_NOS': 'PPL',
    }

    def __init__(self, api_key: str, request_delay: float = 0.5):
        """
        Initialize the football-data.org client.

        Args:
            api_key: API key for football-data.org
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
            'X-Auth-Token': self.api_key,
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
            endpoint: API endpoint (e.g., '/competitions/PL/matches')
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            FootballDataError: If request fails
            RateLimitError: If rate limit is exceeded
        """
        self._rate_limit_check()
        url = f"{self.BASE_URL}{endpoint}"

        try:
            logger.debug(f"GET {url}")
            response = self.session.get(url, params=params, timeout=10)

            # Check for rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")

            response.raise_for_status()
            return response.json()

        except requests.Timeout:
            logger.error(f"Timeout: {url}")
            raise FootballDataError(f"Request timeout: {url}")
        except requests.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            raise FootballDataError(f"Request error: {e}")

    def get_current_matches(self, league_code: str, status: str = 'SCHEDULED') -> List[Dict[str, Any]]:
        """
        Get current or upcoming matches for a league.

        Args:
            league_code: League code (e.g., 'EPL')
            status: Match status ('SCHEDULED', 'LIVE', 'FINISHED', 'POSTPONED')

        Returns:
            List of match dictionaries

        Raises:
            FootballDataError: If API request fails
        """
        if league_code not in self.LEAGUE_CODES:
            raise ValueError(f"Unknown league code: {league_code}")

        api_league = self.LEAGUE_CODES[league_code]
        try:
            response = self._get(
                f'/competitions/{api_league}/matches',
                params={'status': status}
            )

            matches = response.get('matches', [])
            logger.info(f"Retrieved {len(matches)} {status} matches for {league_code}")
            return matches

        except FootballDataError as e:
            logger.error(f"Failed to get matches for {league_code}: {e}")
            raise

    def get_standings(self, league_code: str) -> List[Dict[str, Any]]:
        """
        Get league standings.

        Args:
            league_code: League code (e.g., 'EPL')

        Returns:
            List of team standings

        Raises:
            FootballDataError: If API request fails
        """
        if league_code not in self.LEAGUE_CODES:
            raise ValueError(f"Unknown league code: {league_code}")

        api_league = self.LEAGUE_CODES[league_code]
        try:
            response = self._get(f'/competitions/{api_league}/standings')

            # Extract standings table
            standings = []
            if 'standings' in response and response['standings']:
                for table in response['standings']:
                    standings.extend(table.get('table', []))

            logger.info(f"Retrieved {len(standings)} team standings for {league_code}")
            return standings

        except FootballDataError as e:
            logger.error(f"Failed to get standings for {league_code}: {e}")
            raise

    def get_match_details(self, match_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific match.

        Args:
            match_id: Match ID from API

        Returns:
            Dictionary with match details

        Raises:
            FootballDataError: If API request fails
        """
        try:
            response = self._get(f'/matches/{match_id}')
            logger.info(f"Retrieved details for match {match_id}")
            return response

        except FootballDataError as e:
            logger.error(f"Failed to get match details for {match_id}: {e}")
            raise

    def get_team_info(self, team_id: int) -> Dict[str, Any]:
        """
        Get information about a specific team.

        Args:
            team_id: Team ID from API

        Returns:
            Dictionary with team information

        Raises:
            FootballDataError: If API request fails
        """
        try:
            response = self._get(f'/teams/{team_id}')
            logger.info(f"Retrieved info for team {team_id}")
            return response

        except FootballDataError as e:
            logger.error(f"Failed to get team info for {team_id}: {e}")
            raise

    def get_player_statistics(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get player statistics for a team.

        Args:
            team_id: Team ID from API

        Returns:
            List of player statistics

        Raises:
            FootballDataError: If API request fails
        """
        try:
            response = self._get(f'/teams/{team_id}')
            players = response.get('squad', [])
            logger.info(f"Retrieved {len(players)} players for team {team_id}")
            return players

        except FootballDataError as e:
            logger.error(f"Failed to get player stats for team {team_id}: {e}")
            raise

    def get_all_matches_for_date_range(
        self,
        league_code: str,
        date_from: str,
        date_to: str
    ) -> List[Dict[str, Any]]:
        """
        Get all matches for a league within a date range.

        Args:
            league_code: League code (e.g., 'EPL')
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            List of matches

        Raises:
            FootballDataError: If API request fails
        """
        if league_code not in self.LEAGUE_CODES:
            raise ValueError(f"Unknown league code: {league_code}")

        api_league = self.LEAGUE_CODES[league_code]
        try:
            response = self._get(
                f'/competitions/{api_league}/matches',
                params={
                    'dateFrom': date_from,
                    'dateTo': date_to
                }
            )

            matches = response.get('matches', [])
            logger.info(
                f"Retrieved {len(matches)} matches for {league_code} "
                f"from {date_from} to {date_to}"
            )
            return matches

        except FootballDataError as e:
            logger.error(
                f"Failed to get matches for {league_code} "
                f"from {date_from} to {date_to}: {e}"
            )
            raise

    def get_head_to_head(self, team_id_1: int, team_id_2: int) -> List[Dict[str, Any]]:
        """
        Get head-to-head match history between two teams.

        Args:
            team_id_1: First team ID
            team_id_2: Second team ID

        Returns:
            List of head-to-head matches

        Raises:
            FootballDataError: If API request fails
        """
        try:
            response = self._get(
                f'/teams/{team_id_1}/matches',
                params={'opposition': team_id_2}
            )

            matches = response.get('matches', [])
            logger.info(f"Retrieved {len(matches)} h2h matches for teams {team_id_1} vs {team_id_2}")
            return matches

        except FootballDataError as e:
            logger.error(
                f"Failed to get h2h matches for {team_id_1} vs {team_id_2}: {e}"
            )
            raise
