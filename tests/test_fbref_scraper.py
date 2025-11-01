"""
Unit tests for FBref scraper module.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.scraper.fbref_scraper import (
    FbrefScraper,
    FbrefScraperError,
    RateLimitError,
)


@pytest.fixture
def scraper():
    """Create a FBref scraper instance for testing."""
    return FbrefScraper(request_delay=0)  # No delay for tests


class TestFbrefScraperUtilities:
    """Test utility methods in FBref scraper."""

    def test_parse_season_year_with_dash(self):
        """Test parsing season format with dash."""
        assert FbrefScraper._parse_season_year('2023-24') == '24'

    def test_parse_season_year_single_year(self):
        """Test parsing single year format."""
        assert FbrefScraper._parse_season_year('2024') == '24'

    def test_get_league_table_id(self):
        """Test league table ID mapping."""
        assert FbrefScraper._get_league_table_id('EPL') == 'EPL'
        assert FbrefScraper._get_league_table_id('LA_LIGA') == 'La_Liga'
        assert FbrefScraper._get_league_table_id('SERIE_A') == 'Serie_A'

    def test_parse_date_with_iso_format(self):
        """Test parsing ISO date format."""
        date_obj = FbrefScraper._parse_date('2023-08-12')
        assert date_obj is not None
        assert date_obj.year == 2023
        assert date_obj.month == 8
        assert date_obj.day == 12

    def test_parse_date_invalid_format(self):
        """Test parsing invalid date format."""
        result = FbrefScraper._parse_date('invalid-date')
        assert result is None

    def test_safe_int_valid(self):
        """Test converting valid integer strings."""
        assert FbrefScraper._safe_int('42') == 42
        assert FbrefScraper._safe_int('  100  ') == 100

    def test_safe_int_invalid(self):
        """Test converting invalid integer strings."""
        assert FbrefScraper._safe_int('abc') == 0
        assert FbrefScraper._safe_int('') == 0
        assert FbrefScraper._safe_int(None) == 0

    def test_safe_float_valid(self):
        """Test converting valid float strings."""
        assert FbrefScraper._safe_float('42.5') == 42.5
        assert FbrefScraper._safe_float('60%') == 60.0

    def test_safe_float_invalid(self):
        """Test converting invalid float strings."""
        assert FbrefScraper._safe_float('abc') == 0.0
        assert FbrefScraper._safe_float('') == 0.0


class TestFbrefScraperRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_enforcement(self, scraper):
        """Test that rate limiting enforces delays."""
        scraper.request_delay = 0.1
        import time

        start = time.time()
        scraper._rate_limit_check()
        scraper._rate_limit_check()
        elapsed = time.time() - start

        # Should have at least 0.1 seconds of delay
        assert elapsed >= 0.1

    def test_no_delay_on_first_request(self, scraper):
        """Test that first request has no delay."""
        import time

        scraper.request_delay = 1.0
        start = time.time()
        scraper._rate_limit_check()
        elapsed = time.time() - start

        # First request should be fast
        assert elapsed < 0.1


class TestFbrefScraperDataFetching:
    """Test data fetching and parsing."""

    @patch('src.scraper.fbref_scraper.requests.Session.get')
    def test_fetch_url_success(self, mock_get, scraper):
        """Test successful URL fetching."""
        # Mock response
        mock_response = Mock()
        mock_response.content = b'<html><body>Test</body></html>'
        mock_get.return_value = mock_response

        result = scraper._fetch_url('http://example.com')
        assert result is not None
        assert 'Test' in str(result)

    @patch('src.scraper.fbref_scraper.requests.Session.get')
    def test_fetch_url_timeout(self, mock_get, scraper):
        """Test URL fetching timeout."""
        import requests
        mock_get.side_effect = requests.Timeout()

        with pytest.raises(FbrefScraperError):
            scraper._fetch_url('http://example.com')

    @patch('src.scraper.fbref_scraper.requests.Session.get')
    def test_fetch_url_connection_error(self, mock_get, scraper):
        """Test URL fetching connection error."""
        import requests
        mock_get.side_effect = requests.ConnectionError()

        with pytest.raises(FbrefScraperError):
            scraper._fetch_url('http://example.com')


class TestFbrefScraperLeagueStandings:
    """Test league standings scraping."""

    @patch.object(FbrefScraper, '_fetch_url')
    def test_scrape_league_standings_success(self, mock_fetch, scraper):
        """Test successful league standings scraping."""
        from bs4 import BeautifulSoup

        # Create mock HTML with standings table
        html = '''
        <html>
            <table id="sched_EPL">
                <tr><th>Column Headers</th></tr>
                <tr>
                    <td></td><td></td><td></td><td></td><td></td>
                    <td>Manchester United</td><td>5</td><td>3</td><td>1</td><td>1</td>
                    <td>10</td><td>5</td><td>5</td><td>10</td>
                </tr>
            </table>
        </html>
        '''
        mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

        result = scraper.scrape_league_standings('EPL', '2023-24')
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]['name'] == 'Manchester United'

    @patch.object(FbrefScraper, '_fetch_url')
    def test_scrape_league_standings_unknown_league(self, mock_fetch, scraper):
        """Test scraping unknown league code."""
        with pytest.raises(FbrefScraperError):
            scraper.scrape_league_standings('UNKNOWN_LEAGUE', '2023-24')

    @patch.object(FbrefScraper, '_fetch_url')
    def test_scrape_league_standings_no_table(self, mock_fetch, scraper):
        """Test scraping when table not found."""
        from bs4 import BeautifulSoup

        html = '<html><body>No table here</body></html>'
        mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

        result = scraper.scrape_league_standings('EPL', '2023-24')
        assert result == []


class TestFbrefScraperTeamMatches:
    """Test team match scraping."""

    @patch.object(FbrefScraper, '_fetch_url')
    def test_scrape_team_matches_success(self, mock_fetch, scraper):
        """Test successful team match scraping."""
        from bs4 import BeautifulSoup

        html = '''
        <html>
            <table id="matchlogs_all">
                <tr><th>Headers</th></tr>
                <tr>
                    <td></td><td>2023-08-12</td><td>15:00</td><td>Sat</td>
                    <td>Premier League</td><td>1</td><td>Home</td>
                    <td>Liverpool</td><td>Win</td><td>2</td><td>1</td>
                </tr>
            </table>
        </html>
        '''
        mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

        result = scraper.scrape_team_matches('http://example.com/team')
        assert isinstance(result, list)
        assert len(result) > 0

    @patch.object(FbrefScraper, '_fetch_url')
    def test_scrape_team_matches_no_table(self, mock_fetch, scraper):
        """Test scraping when match table not found."""
        from bs4 import BeautifulSoup

        html = '<html><body>No matches</body></html>'
        mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

        result = scraper.scrape_team_matches('http://example.com/team')
        assert result == []


class TestFbrefScraperMatchDetails:
    """Test match details scraping."""

    @patch.object(FbrefScraper, '_fetch_url')
    def test_scrape_match_details_success(self, mock_fetch, scraper):
        """Test successful match details scraping."""
        from bs4 import BeautifulSoup

        html = '''
        <html>
            <h1>Manchester United vs Liverpool</h1>
            <table class="stats_table">
                <tr><td>Shots</td><td>15</td><td>12</td></tr>
                <tr><td>Possession</td><td>55%</td><td>45%</td></tr>
            </table>
        </html>
        '''
        mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

        result = scraper.scrape_match_details('http://example.com/match')
        assert isinstance(result, dict)
        assert 'url' in result
        assert 'home_stats' in result
        assert 'away_stats' in result

    @patch.object(FbrefScraper, '_fetch_url')
    def test_scrape_match_details_parse_error(self, mock_fetch, scraper):
        """Test handling of parse errors."""
        from bs4 import BeautifulSoup

        html = '<html><body>Invalid</body></html>'
        mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

        # Should not raise, should return basic structure
        result = scraper.scrape_match_details('http://example.com/match')
        assert isinstance(result, dict)
