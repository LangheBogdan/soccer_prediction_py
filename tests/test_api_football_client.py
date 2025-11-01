"""
Unit tests for api-football.com API client.
"""

import pytest
from unittest.mock import Mock, patch

from src.clients.api_football_client import (
    ApiFootballClient,
    ApiFootballError,
    RateLimitError,
)


@pytest.fixture
def client():
    """Create an api-football.com client for testing."""
    return ApiFootballClient(api_key='test_key', request_delay=0)


class TestApiFootballClientInitialization:
    """Test client initialization."""

    def test_init_with_valid_key(self):
        """Test initialization with valid API key."""
        client = ApiFootballClient('test_key')
        assert client.api_key == 'test_key'
        assert client.session is not None

    def test_init_with_empty_key(self):
        """Test initialization with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ApiFootballClient('')

    def test_init_with_none_key(self):
        """Test initialization with None API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ApiFootballClient(None)

    def test_session_headers(self):
        """Test that session headers are set correctly."""
        client = ApiFootballClient('test_key')
        assert 'X-RapidAPI-Key' in client.session.headers
        assert client.session.headers['X-RapidAPI-Key'] == 'test_key'
        assert client.session.headers['X-RapidAPI-Host'] == ApiFootballClient.RAPIDAPI_HOST


class TestApiFootballClientLeagueMapping:
    """Test league ID mapping."""

    def test_league_id_mapping(self):
        """Test that league codes map to correct IDs."""
        assert ApiFootballClient.LEAGUE_IDS['EPL'] == 39
        assert ApiFootballClient.LEAGUE_IDS['LA_LIGA'] == 140
        assert ApiFootballClient.LEAGUE_IDS['SERIE_A'] == 135
        assert ApiFootballClient.LEAGUE_IDS['BUNDESLIGA'] == 78
        assert ApiFootballClient.LEAGUE_IDS['LIGUE_1'] == 61


class TestApiFootballClientRateLimiting:
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


class TestApiFootballClientAPIRequests:
    """Test API request handling."""

    @patch('src.clients.api_football_client.requests.Session.get')
    def test_get_request_success(self, mock_get, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': [{'id': 1}],
            'errors': {}
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = client._get('/fixtures')
        assert 'response' in result

    @patch('src.clients.api_football_client.requests.Session.get')
    def test_get_request_rate_limit(self, mock_get, client):
        """Test API request with rate limit response."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError):
            client._get('/fixtures')

    @patch('src.clients.api_football_client.requests.Session.get')
    def test_get_request_bad_request(self, mock_get, client):
        """Test API request with bad request response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'errors': ['Bad request']}
        mock_response.text = 'Bad request'
        mock_get.return_value = mock_response

        with pytest.raises(ApiFootballError, match="Bad request"):
            client._get('/fixtures')

    @patch('src.clients.api_football_client.requests.Session.get')
    def test_get_request_api_error(self, mock_get, client):
        """Test API request with API-level error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'errors': {'limit': 'Rate limit exceeded'},
            'response': []
        }
        mock_get.return_value = mock_response

        with pytest.raises(ApiFootballError, match="API error"):
            client._get('/fixtures')

    @patch('src.clients.api_football_client.requests.Session.get')
    def test_get_request_timeout(self, mock_get, client):
        """Test API request timeout."""
        import requests
        mock_get.side_effect = requests.Timeout()

        with pytest.raises(ApiFootballError, match="Request timeout"):
            client._get('/fixtures')


class TestApiFootballClientFixtures:
    """Test fixture-related API methods."""

    @patch.object(ApiFootballClient, '_get')
    def test_get_fixtures(self, mock_get, client):
        """Test getting fixtures."""
        mock_get.return_value = {
            'response': [
                {'id': 1, 'fixture': {'date': '2023-08-12'}},
                {'id': 2, 'fixture': {'date': '2023-08-13'}},
            ]
        }

        result = client.get_fixtures(39, 2023)
        assert len(result) == 2

    @patch.object(ApiFootballClient, '_get')
    def test_get_fixtures_with_status(self, mock_get, client):
        """Test getting fixtures with status filter."""
        mock_get.return_value = {'response': []}

        client.get_fixtures(39, 2023, status='FINISHED')
        mock_get.assert_called_once()

    @patch.object(ApiFootballClient, '_get')
    def test_get_fixture_details(self, mock_get, client):
        """Test getting fixture details."""
        mock_get.return_value = {
            'response': [
                {
                    'id': 1,
                    'fixture': {'id': 1, 'date': '2023-08-12'},
                    'teams': {
                        'home': {'id': 1, 'name': 'Team A'},
                        'away': {'id': 2, 'name': 'Team B'},
                    },
                    'goals': {'home': 2, 'away': 1},
                }
            ]
        }

        result = client.get_fixture_details(1)
        assert result['id'] == 1

    @patch.object(ApiFootballClient, '_get')
    def test_get_fixture_details_not_found(self, mock_get, client):
        """Test getting non-existent fixture."""
        mock_get.return_value = {'response': []}

        with pytest.raises(ApiFootballError, match="Fixture not found"):
            client.get_fixture_details(999)


class TestApiFootballClientStandings:
    """Test standings-related API methods."""

    @patch.object(ApiFootballClient, '_get')
    def test_get_league_standings(self, mock_get, client):
        """Test getting league standings."""
        mock_get.return_value = {
            'response': [
                {
                    'league': {
                        'standings': [
                            [
                                {'team': {'id': 1, 'name': 'Team A'}, 'points': 30},
                                {'team': {'id': 2, 'name': 'Team B'}, 'points': 25},
                            ]
                        ]
                    }
                }
            ]
        }

        result = client.get_league_standings(39, 2023)
        assert len(result) == 2


class TestApiFootballClientTeamStatistics:
    """Test team statistics API methods."""

    @patch.object(ApiFootballClient, '_get')
    def test_get_team_statistics(self, mock_get, client):
        """Test getting team statistics."""
        mock_get.return_value = {
            'team': {'id': 1, 'name': 'Team A'},
            'statistics': [
                {'type': 'Shots On Goal', 'value': 5}
            ]
        }

        result = client.get_team_statistics(39, 1, 2023)
        assert isinstance(result, dict)
        mock_get.assert_called_once()

    @patch.object(ApiFootballClient, '_get')
    def test_get_player_statistics(self, mock_get, client):
        """Test getting player statistics."""
        mock_get.return_value = {
            'player': {'id': 1, 'name': 'Player A'},
            'statistics': [{'games': {'minutes': 500}}]
        }

        result = client.get_player_statistics(1, 39, 2023)
        assert isinstance(result, dict)


class TestApiFootballClientHeadToHead:
    """Test head-to-head API methods."""

    @patch.object(ApiFootballClient, '_get')
    def test_get_head_to_head(self, mock_get, client):
        """Test getting head-to-head match history."""
        mock_get.return_value = {
            'response': [
                {'id': 1, 'teams': {'home': {'id': 1}, 'away': {'id': 2}}},
                {'id': 2, 'teams': {'home': {'id': 2}, 'away': {'id': 1}}},
            ]
        }

        result = client.get_head_to_head(1, 2)
        assert len(result) == 2


class TestApiFootballClientOdds:
    """Test odds-related API methods."""

    @patch.object(ApiFootballClient, '_get')
    def test_get_odds(self, mock_get, client):
        """Test getting betting odds."""
        mock_get.return_value = {
            'response': [
                {
                    'fixture': {'id': 1},
                    'bookmakers': [
                        {
                            'name': 'Bet365',
                            'bets': [
                                {'name': '1X2', 'values': [
                                    {'odd': 2.50, 'value': 'Home'},
                                    {'odd': 3.00, 'value': 'Draw'},
                                    {'odd': 2.75, 'value': 'Away'},
                                ]}
                            ]
                        }
                    ]
                }
            ]
        }

        result = client.get_odds(1)
        assert isinstance(result, list)


class TestApiFootballClientDateRange:
    """Test date range queries."""

    @patch.object(ApiFootballClient, '_get')
    def test_get_fixtures_by_date(self, mock_get, client):
        """Test getting fixtures for a date range."""
        mock_get.return_value = {
            'response': [
                {'id': 1, 'fixture': {'date': '2023-08-12T15:00:00Z'}},
                {'id': 2, 'fixture': {'date': '2023-08-13T15:00:00Z'}},
            ]
        }

        result = client.get_fixtures_by_date(39, '2023-08-12', '2023-08-13')
        assert len(result) == 2


class TestApiFootballClientInjuries:
    """Test injuries API methods."""

    @patch.object(ApiFootballClient, '_get')
    def test_get_injuries(self, mock_get, client):
        """Test getting player injuries."""
        mock_get.return_value = {
            'response': [
                {'player': {'id': 1, 'name': 'Player A'}, 'type': 'Injury'},
                {'player': {'id': 2, 'name': 'Player B'}, 'type': 'Suspension'},
            ]
        }

        result = client.get_injuries(39, 2023)
        assert len(result) == 2
