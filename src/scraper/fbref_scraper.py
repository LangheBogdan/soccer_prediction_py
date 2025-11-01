"""
FBref.com web scraper for extracting football statistics.

This module provides functionality to scrape league standings, team statistics,
and historical match data from FBref.com (Football Reference).

Rate limiting: FBref allows reasonable scraping; we add delays to be respectful.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

import requests
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)


class FbrefScraperError(Exception):
    """Base exception for FBref scraper errors."""
    pass


class RateLimitError(FbrefScraperError):
    """Raised when rate limit is exceeded."""
    pass


class FbrefScraper:
    """
    Scraper for FBref.com football statistics.

    Attributes:
        base_url (str): Base URL for FBref
        request_delay (float): Delay between requests in seconds (respect rate limits)
        timeout (int): Request timeout in seconds
    """

    BASE_URL = "https://fbref.com/en"
    REQUEST_DELAY = 2.0  # 2 seconds between requests
    TIMEOUT = 10

    def __init__(self, request_delay: float = REQUEST_DELAY):
        """
        Initialize the FBref scraper.

        Args:
            request_delay: Delay between requests in seconds
        """
        self.request_delay = request_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def _rate_limit_check(self) -> None:
        """Enforce rate limiting with delay between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            delay = self.request_delay - elapsed
            logger.debug(f"Rate limit delay: {delay:.2f}s")
            time.sleep(delay)
        self.last_request_time = time.time()

    def _fetch_url(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a URL with rate limiting.

        Args:
            url: URL to fetch

        Returns:
            BeautifulSoup object or None if request fails

        Raises:
            FbrefScraperError: If request fails
        """
        self._rate_limit_check()
        try:
            logger.debug(f"Fetching: {url}")
            response = self.session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except requests.Timeout:
            logger.error(f"Timeout fetching {url}")
            raise FbrefScraperError(f"Request timeout: {url}")
        except requests.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            raise FbrefScraperError(f"Request error: {e}")

    def scrape_league_standings(self, league_code: str, season: str) -> List[Dict[str, Any]]:
        """
        Scrape league standings and team statistics.

        Args:
            league_code: League code (e.g., 'EPL' for English Premier League)
            season: Season (e.g., '2023-24')

        Returns:
            List of team data dictionaries with standings and stats

        Example:
            >>> scraper = FbrefScraper()
            >>> teams = scraper.scrape_league_standings('EPL', '2023-24')
        """
        # Convert season format if needed (e.g., 2023-24 -> 2024)
        season_year = self._parse_season_year(season)

        # FBref URLs for different leagues
        league_urls = {
            'EPL': f'{self.BASE_URL}/comps/9/{season_year}/schedule/',
            'LA_LIGA': f'{self.BASE_URL}/comps/12/{season_year}/schedule/',
            'SERIE_A': f'{self.BASE_URL}/comps/11/{season_year}/schedule/',
            'BUNDESLIGA': f'{self.BASE_URL}/comps/20/{season_year}/schedule/',
            'LIGUE_1': f'{self.BASE_URL}/comps/13/{season_year}/schedule/',
        }

        if league_code not in league_urls:
            raise FbrefScraperError(f"Unknown league code: {league_code}")

        url = league_urls[league_code]
        soup = self._fetch_url(url)
        if not soup:
            raise FbrefScraperError(f"Failed to fetch standings for {league_code}")

        teams_data = []
        try:
            # Look for table with standings
            table = soup.find('table', {'id': 'sched_' + self._get_league_table_id(league_code)})
            if not table:
                logger.warning(f"Could not find standings table for {league_code}")
                return teams_data

            rows = table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 8:
                    continue

                team_name = cells[5].get_text(strip=True)
                if not team_name:
                    continue

                team_data = {
                    'name': team_name,
                    'matches_played': self._safe_int(cells[6].get_text(strip=True)),
                    'wins': self._safe_int(cells[7].get_text(strip=True)),
                    'draws': self._safe_int(cells[8].get_text(strip=True)) if len(cells) > 8 else 0,
                    'losses': self._safe_int(cells[9].get_text(strip=True)) if len(cells) > 9 else 0,
                    'goals_for': self._safe_int(cells[10].get_text(strip=True)) if len(cells) > 10 else 0,
                    'goals_against': self._safe_int(cells[11].get_text(strip=True)) if len(cells) > 11 else 0,
                    'goal_difference': self._safe_int(cells[12].get_text(strip=True)) if len(cells) > 12 else 0,
                    'points': self._safe_int(cells[13].get_text(strip=True)) if len(cells) > 13 else 0,
                }
                teams_data.append(team_data)

        except (AttributeError, ValueError) as e:
            logger.error(f"Error parsing standings table: {e}")
            raise FbrefScraperError(f"Failed to parse standings: {e}")

        logger.info(f"Scraped {len(teams_data)} teams from {league_code}")
        return teams_data

    def scrape_team_matches(self, team_url: str) -> List[Dict[str, Any]]:
        """
        Scrape match history for a specific team.

        Args:
            team_url: Team page URL on FBref

        Returns:
            List of match data dictionaries

        Example:
            >>> url = "https://fbref.com/en/squads/..."
            >>> matches = scraper.scrape_team_matches(url)
        """
        soup = self._fetch_url(team_url)
        if not soup:
            raise FbrefScraperError(f"Failed to fetch team page: {team_url}")

        matches = []
        try:
            # Find the match table
            table = soup.find('table', {'id': 'matchlogs_all'})
            if not table:
                logger.warning(f"No match log table found for {team_url}")
                return matches

            rows = table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 10:
                    continue

                try:
                    match_data = {
                        'date': self._parse_date(cells[1].get_text(strip=True)),
                        'time': cells[2].get_text(strip=True),
                        'day': cells[3].get_text(strip=True),
                        'competition': cells[4].get_text(strip=True),
                        'round': cells[5].get_text(strip=True),
                        'venue': cells[6].get_text(strip=True),
                        'opponent': cells[7].get_text(strip=True),
                        'result': cells[8].get_text(strip=True),
                        'goals_for': self._safe_int(cells[9].get_text(strip=True)),
                        'goals_against': self._safe_int(cells[10].get_text(strip=True)) if len(cells) > 10 else None,
                    }
                    matches.append(match_data)
                except (ValueError, IndexError):
                    continue

        except AttributeError as e:
            logger.error(f"Error parsing match table: {e}")
            raise FbrefScraperError(f"Failed to parse matches: {e}")

        logger.info(f"Scraped {len(matches)} matches from team")
        return matches

    def scrape_match_details(self, match_url: str) -> Dict[str, Any]:
        """
        Scrape detailed statistics for a specific match.

        Args:
            match_url: Match report URL on FBref

        Returns:
            Dictionary with detailed match statistics

        Example:
            >>> details = scraper.scrape_match_details(url)
        """
        soup = self._fetch_url(match_url)
        if not soup:
            raise FbrefScraperError(f"Failed to fetch match page: {match_url}")

        match_details = {
            'url': match_url,
            'home_team': None,
            'away_team': None,
            'home_goals': None,
            'away_goals': None,
            'home_stats': {},
            'away_stats': {},
        }

        try:
            # Extract score and teams from page title/header
            title = soup.find('h1')
            if title:
                match_text = title.get_text(strip=True)
                match_details['title'] = match_text

            # Try to find the stats table
            stats_tables = soup.find_all('table', {'class': 'stats_table'})

            for table in stats_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        stat_name = cells[0].get_text(strip=True)
                        home_value = cells[1].get_text(strip=True)
                        away_value = cells[2].get_text(strip=True)

                        if stat_name:
                            match_details['home_stats'][stat_name] = self._safe_float(home_value)
                            match_details['away_stats'][stat_name] = self._safe_float(away_value)

        except AttributeError as e:
            logger.error(f"Error parsing match details: {e}")
            raise FbrefScraperError(f"Failed to parse match details: {e}")

        return match_details

    # Utility methods
    @staticmethod
    def _parse_season_year(season: str) -> str:
        """
        Parse season string to year for URL construction.

        Args:
            season: Season string (e.g., '2023-24')

        Returns:
            Year string (e.g., '2024')
        """
        if '-' in season:
            return season.split('-')[1]
        return season[-2:]

    @staticmethod
    def _get_league_table_id(league_code: str) -> str:
        """Get the FBref table ID for a league."""
        league_ids = {
            'EPL': 'EPL',
            'LA_LIGA': 'La_Liga',
            'SERIE_A': 'Serie_A',
            'BUNDESLIGA': 'Bundesliga',
            'LIGUE_1': 'Ligue_1',
        }
        return league_ids.get(league_code, '')

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime object.

        Args:
            date_str: Date string (e.g., '2023-08-12')

        Returns:
            Datetime object or None if parsing fails
        """
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d %b %Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _safe_int(value: str) -> int:
        """Safely convert string to integer."""
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return 0

    @staticmethod
    def _safe_float(value: str) -> float:
        """Safely convert string to float."""
        try:
            return float(value.strip().replace('%', ''))
        except (ValueError, AttributeError):
            return 0.0
