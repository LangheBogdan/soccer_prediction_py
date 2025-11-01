"""
Unit tests for football-data.org API client.
"""

import pytest
from unittest.mock import Mock, patch

from src.clients.football_data_client import (
    FootballDataClient,
    FootballDataError,
    RateLimitError,
)


@pytest.fixture
def client():
    """Create a football-data.org client for testing."""
    return FootballDataClient(api_key='test_key', request_delay=0)


class TestFootballDataClientInitialization:
    """Test client initialization."""

    def test_init_with_valid_key(self):
        """Test initialization with valid API key."""
        client = FootballDataClient('test_key')
        assert client.api_key == 'test_key'
        assert client.session is not None

    def test_init_with_empty_key(self):
        """Test initialization with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            FootballDataClient('')

    def test_init_with_none_key(self):
        """Test initialization with None API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            FootballDataClient(None)


class TestFootballDataClientLeagueMapping:
    """Test league code mapping."""

    def test_league_code_mapping(self):
        """Test that league codes map correctly."""
        assert FootballDataClient.LEAGUE_CODES['EPL'] == 'PL'
        assert FootballDataClient.LEAGUE_CODES['LA_LIGA'] == 'SA'
        assert FootballDataClient.LEAGUE_CODES['SERIE_A'] == 'SA'
        assert FootballDataClient.LEAGUE_CODES['BUNDESLIGA'] == 'BL1'
        assert FootballDataClient.LEAGUE_CODES['LIGUE_1'] == 'FL1'


class TestFootballDataClientRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_enforcement(self, client):
        """Test that rate limiting enforces delays."""
        client.request_delay = 0.1
        import time

        start = time.time()
        client._rate_limit_check()
        client._rate_limit_check()
        elapsed = time.time() - start

        # Should have at least 0.1 seconds of delay
        assert elapsed >= 0.1


class TestFootballDataClientAPIRequests:
    """Test API request handling."""

    @patch('src.clients.football_data_client.requests.Session.get')
    def test_get_request_success(self, mock_get, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {'matches': [{'id': 1}]}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = client._get('/matches')
        assert result == {'matches': [{'id': 1}]}

    @patch('src.clients.football_data_client.requests.Session.get')
    def test_get_request_rate_limit(self, mock_get, client):
        """Test API request with rate limit response."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError):
            client._get('/matches')

    @patch('src.clients.football_data_client.requests.Session.get')
    def test_get_request_timeout(self, mock_get, client):
        """Test API request timeout."""
        import requests
        mock_get.side_effect = requests.Timeout()

        with pytest.raises(FootballDataError, match="Request timeout"):
            client._get('/matches')

    @patch('src.clients.football_data_client.requests.Session.get')
    def test_get_request_connection_error(self, mock_get, client):
        """Test API request connection error."""
        import requests
        mock_get.side_effect = requests.ConnectionError()

        with pytest.raises(FootballDataError, match="Request error"):
            client._get('/matches')


class TestFootballDataClientMatches:
    """Test match-related API methods."""

    @patch.object(FootballDataClient, '_get')
    def test_get_current_matches(self, mock_get, client):
        """Test getting current matches."""
        mock_get.return_value = {
            'matches': [
                {'id': 1, 'homeTeam': {'name': 'Team A'}, 'awayTeam': {'name': 'Team B'}},
            ]
        }

        result = client.get_current_matches('EPL', status='SCHEDULED')
        assert len(result) == 1
        assert result[0]['id'] == 1
        mock_get.assert_called_once()

    @patch.object(FootballDataClient, '_get')
    def test_get_current_matches_unknown_league(self, mock_get, client):
        """Test getting matches for unknown league."""
        with pytest.raises(ValueError, match="Unknown league code"):
            client.get_current_matches('UNKNOWN_LEAGUE')

    @patch.object(FootballDataClient, '_get')
    def test_get_match_details(self, mock_get, client):
        """Test getting match details."""
        mock_get.return_value = {
            'id': 123,
            'homeTeam': {'name': 'Team A'},
            'awayTeam': {'name': 'Team B'},
            'score': {'fullTime': {'home': 2, 'away': 1}},
        }

        result = client.get_match_details(123)
        assert result['id'] == 123
        mock_get.assert_called_once()


class TestFootballDataClientStandings:
    """Test standings-related API methods."""

    @patch.object(FootballDataClient, '_get')
    def test_get_standings(self, mock_get, client):
        """Test getting league standings."""
        mock_get.return_value = {
            'standings': [
                {
                    'table': [
                        {'team': {'id': 1, 'name': 'Team A'}, 'points': 30},
                        {'team': {'id': 2, 'name': 'Team B'}, 'points': 25},
                    ]
                }
            ]
        }

        result = client.get_standings('EPL')
        assert len(result) == 2
        assert result[0]['team']['name'] == 'Team A'

    @patch.object(FootballDataClient, '_get')
    def test_get_standings_unknown_league(self, mock_get, client):
        """Test getting standings for unknown league."""
        with pytest.raises(ValueError, match="Unknown league code"):
            client.get_standings('UNKNOWN_LEAGUE')


class TestFootballDataClientTeamInfo:
    """Test team-related API methods."""

    @patch.object(FootballDataClient, '_get')
    def test_get_team_info(self, mock_get, client):
        """Test getting team information."""
        mock_get.return_value = {
            'id': 1,
            'name': 'Team A',
            'founded': 1990,
        }

        result = client.get_team_info(1)
        assert result['id'] == 1
        assert result['name'] == 'Team A'

    @patch.object(FootballDataClient, '_get')
    def test_get_player_statistics(self, mock_get, client):
        """Test getting player statistics."""
        mock_get.return_value = {
            'squad': [
                {'id': 1, 'name': 'Player A', 'position': 'Forward'},
                {'id': 2, 'name': 'Player B', 'position': 'Midfielder'},
            ]
        }

        result = client.get_player_statistics(1)
        assert len(result) == 2
        assert result[0]['name'] == 'Player A'


class TestFootballDataClientDateRange:
    """Test date range queries."""

    @patch.object(FootballDataClient, '_get')
    def test_get_all_matches_for_date_range(self, mock_get, client):
        """Test getting matches for a date range."""
        mock_get.return_value = {
            'matches': [
                {'id': 1, 'utcDate': '2023-08-12T15:00:00Z'},
                {'id': 2, 'utcDate': '2023-08-13T15:00:00Z'},
            ]
        }

        result = client.get_all_matches_for_date_range('EPL', '2023-08-12', '2023-08-13')
        assert len(result) == 2

    @patch.object(FootballDataClient, '_get')
    def test_get_all_matches_for_date_range_unknown_league(self, mock_get, client):
        """Test date range query for unknown league."""
        with pytest.raises(ValueError, match="Unknown league code"):
            client.get_all_matches_for_date_range('UNKNOWN', '2023-08-12', '2023-08-13')


class TestFootballDataClientHeadToHead:
    """Test head-to-head queries."""

    @patch.object(FootballDataClient, '_get')
    def test_get_head_to_head(self, mock_get, client):
        """Test getting head-to-head match history."""
        mock_get.return_value = {
            'matches': [
                {'id': 1, 'homeTeam': {'id': 1}, 'awayTeam': {'id': 2}},
                {'id': 2, 'homeTeam': {'id': 2}, 'awayTeam': {'id': 1}},
            ]
        }

        result = client.get_head_to_head(1, 2)
        assert len(result) == 2
