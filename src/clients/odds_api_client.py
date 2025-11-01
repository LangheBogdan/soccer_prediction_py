"""
Client for the-odds-api.com API (RapidAPI).

This module provides functionality to fetch betting odds from multiple bookmakers
for football matches across various leagues.

API Documentation: https://rapidapi.com/api-sports/api/api-odds
"""

import logging
import time
from typing import Dict, List, Optional, Any

import requests

# Configure logging
logger = logging.getLogger(__name__)


class OddsApiError(Exception):
    """Base exception for the-odds-api.com API errors."""
    pass


class RateLimitError(OddsApiError):
    """Raised when API rate limit is exceeded."""
    pass


class OddsApiClient:
    """
    Client for the-odds-api.com API (RapidAPI).

    Provides betting odds from multiple bookmakers for football matches.

    Attributes:
        api_key (str): RapidAPI key for the-odds-api
        api_host (str): RapidAPI host header
        base_url (str): Base URL for API endpoints
    """

    BASE_URL = "https://api-odds.p.rapidapi.com"
    RAPIDAPI_HOST = "api-odds.p.rapidapi.com"

    # Sport IDs in the-odds-api
    SPORT_IDS = {
        'soccer': 'soccer',
        'football': 'soccer',
    }

    # League/region mappings for soccer
    LEAGUE_IDS = {
        'EPL': 'soccer_epl',
        'LA_LIGA': 'soccer_spain_la_liga',
        'SERIE_A': 'soccer_italy_serie_a',
        'BUNDESLIGA': 'soccer_germany_bundesliga',
        'LIGUE_1': 'soccer_france_ligue_one',
        'EREDIVISIE': 'soccer_netherlands_eredivisie',
        'LIGA_NOS': 'soccer_portugal_liga_nos',
        'CHAMPIONS_LEAGUE': 'soccer_uefa_champs_league',
    }

    # Bookmakers available in the-odds-api
    BOOKMAKERS = [
        'bet365',
        'draftkings',
        'fanduel',
        'betmgm',
        'pointsbet',
        'betrivers',
        'caesars',
        'unibet',
        'betfair',
        'pinnacle',
        'bovada',
        'barstool',
    ]

    def __init__(self, api_key: str, request_delay: float = 0.5):
        """
        Initialize the odds API client.

        Args:
            api_key: RapidAPI key for the-odds-api
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
            endpoint: API endpoint (e.g., '/odds')
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            OddsApiError: If request fails
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
                raise OddsApiError(f"Bad request: {response.text}")

            response.raise_for_status()
            data = response.json()

            # Check for API-level errors in response
            if isinstance(data, dict) and 'errors' in data and data['errors']:
                errors = data.get('errors', {})
                logger.error(f"API errors: {errors}")
                raise OddsApiError(f"API error: {errors}")

            return data

        except requests.Timeout:
            logger.error(f"Timeout: {url}")
            raise OddsApiError(f"Request timeout: {url}")
        except requests.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            raise OddsApiError(f"Request error: {e}")

    def get_sports(self) -> List[Dict[str, Any]]:
        """
        Get list of available sports.

        Returns:
            List of sports with IDs and names

        Raises:
            OddsApiError: If API request fails
        """
        try:
            response = self._get('/sports')
            sports = response if isinstance(response, list) else response.get('sports', [])
            logger.info(f"Retrieved {len(sports)} sports")
            return sports

        except OddsApiError as e:
            logger.error(f"Failed to get sports: {e}")
            raise

    def get_leagues(self) -> List[Dict[str, Any]]:
        """
        Get list of available soccer leagues.

        Returns:
            List of soccer leagues

        Raises:
            OddsApiError: If API request fails
        """
        try:
            response = self._get('/sports')
            sports = response if isinstance(response, list) else response.get('sports', [])

            # Filter for soccer sports
            leagues = [
                sport for sport in sports
                if sport.get('key', '').startswith('soccer_')
            ]
            logger.info(f"Retrieved {len(leagues)} soccer leagues")
            return leagues

        except OddsApiError as e:
            logger.error(f"Failed to get leagues: {e}")
            raise

    def get_odds(
        self,
        league_id: str,
        bookmakers: Optional[List[str]] = None,
        markets: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get odds for a league.

        Args:
            league_id: League ID (e.g., 'soccer_epl')
            bookmakers: List of bookmaker names to include (optional)
            markets: List of market types ('h2h', 'spreads', 'totals')

        Returns:
            List of odds data for matches

        Raises:
            OddsApiError: If API request fails
        """
        if league_id not in self.LEAGUE_IDS.values() and league_id not in self.LEAGUE_IDS:
            logger.warning(f"Unknown league ID: {league_id}, proceeding anyway")

        try:
            params = {'sport': league_id}

            if bookmakers:
                params['bookmakers'] = ','.join(bookmakers)

            if markets:
                params['markets'] = ','.join(markets)

            response = self._get('/odds', params=params)
            odds_data = response if isinstance(response, list) else response.get('data', [])

            logger.info(f"Retrieved odds for {len(odds_data)} matches in {league_id}")
            return odds_data

        except OddsApiError as e:
            logger.error(f"Failed to get odds for league {league_id}: {e}")
            raise

    def get_odds_for_league_code(
        self,
        league_code: str,
        bookmakers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get odds for a league using standard league code.

        Args:
            league_code: League code (e.g., 'EPL', 'LA_LIGA')
            bookmakers: List of bookmaker names to include

        Returns:
            List of odds data

        Raises:
            OddsApiError: If league code is unknown or request fails
        """
        if league_code not in self.LEAGUE_IDS:
            raise OddsApiError(f"Unknown league code: {league_code}")

        league_id = self.LEAGUE_IDS[league_code]
        return self.get_odds(league_id, bookmakers=bookmakers)

    def get_historical_odds(
        self,
        league_id: str,
        date: str,
        bookmakers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get historical odds for a specific date.

        Args:
            league_id: League ID (e.g., 'soccer_epl')
            date: Date in YYYY-MM-DD format
            bookmakers: List of bookmaker names to include

        Returns:
            List of historical odds

        Raises:
            OddsApiError: If API request fails
        """
        try:
            params = {
                'sport': league_id,
                'date': date,
            }

            if bookmakers:
                params['bookmakers'] = ','.join(bookmakers)

            response = self._get('/odds-history', params=params)
            odds_data = response if isinstance(response, list) else response.get('data', [])

            logger.info(f"Retrieved {len(odds_data)} historical odds for {league_id} on {date}")
            return odds_data

        except OddsApiError as e:
            logger.error(f"Failed to get historical odds: {e}")
            raise

    def get_bookmakers(self) -> List[str]:
        """
        Get list of available bookmakers.

        Returns:
            List of bookmaker names

        Raises:
            OddsApiError: If API request fails
        """
        try:
            response = self._get('/bookmakers')
            bookmakers = response if isinstance(response, list) else response.get('bookmakers', [])

            logger.info(f"Retrieved {len(bookmakers)} available bookmakers")
            return bookmakers

        except OddsApiError as e:
            logger.error(f"Failed to get bookmakers: {e}")
            raise

    def get_event_odds(
        self,
        league_id: str,
        event_id: str,
        bookmakers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get odds for a specific event/match.

        Args:
            league_id: League ID
            event_id: Event/match ID
            bookmakers: List of bookmaker names to include

        Returns:
            Dictionary with odds data for the event

        Raises:
            OddsApiError: If API request fails
        """
        try:
            params = {
                'sport': league_id,
                'eventId': event_id,
            }

            if bookmakers:
                params['bookmakers'] = ','.join(bookmakers)

            response = self._get('/odds', params=params)
            logger.info(f"Retrieved odds for event {event_id}")
            return response

        except OddsApiError as e:
            logger.error(f"Failed to get odds for event {event_id}: {e}")
            raise

    def parse_odds_response(self, odds_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse odds response into a standardized format.

        Args:
            odds_data: Raw odds data from API

        Returns:
            Parsed odds in standardized format

        Example:
            >>> client = OddsApiClient('key')
            >>> parsed = client.parse_odds_response(raw_odds)
            >>> print(parsed['home_win_odds'])
        """
        parsed = {
            'id': odds_data.get('id'),
            'sport_key': odds_data.get('sport_key'),
            'sport_title': odds_data.get('sport_title'),
            'commence_time': odds_data.get('commence_time'),
            'home_team': odds_data.get('home_team'),
            'away_team': odds_data.get('away_team'),
            'bookmakers': [],
        }

        # Parse bookmaker odds
        for bookmaker in odds_data.get('bookmakers', []):
            bm_data = {
                'name': bookmaker.get('title'),
                'last_update': bookmaker.get('last_update'),
                'markets': {},
            }

            # Parse markets (h2h, spreads, totals)
            for market in bookmaker.get('markets', []):
                market_key = market.get('key')
                outcomes = market.get('outcomes', [])

                if market_key == 'h2h':
                    # Match winner market
                    for outcome in outcomes:
                        team = outcome.get('name')
                        odds = outcome.get('price')
                        if team and odds:
                            bm_data['markets'][f'{team}_odds'] = odds
                elif market_key == 'spreads':
                    # Point spread market
                    bm_data['markets']['spreads'] = outcomes
                elif market_key == 'totals':
                    # Over/under market
                    bm_data['markets']['totals'] = outcomes

            parsed['bookmakers'].append(bm_data)

        return parsed

    def get_best_odds(
        self,
        odds_data: Dict[str, Any],
        outcome: str = 'home_win',
    ) -> Optional[float]:
        """
        Get the best odds for a given outcome across all bookmakers.

        Args:
            odds_data: Parsed odds data
            outcome: Outcome type ('home_win', 'draw', 'away_win')

        Returns:
            Best odds value or None if not found

        Example:
            >>> best_odds = client.get_best_odds(parsed_odds, 'home_win')
        """
        best_odds = None

        for bookmaker in odds_data.get('bookmakers', []):
            markets = bookmaker.get('markets', {})
            odds_key = f'{outcome}_odds'

            if odds_key in markets:
                odds_value = markets[odds_key]
                if odds_value and (best_odds is None or odds_value > best_odds):
                    best_odds = odds_value

        return best_odds
