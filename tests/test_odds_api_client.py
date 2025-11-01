"""
Unit tests for the-odds-api.com API client.
"""

import pytest
from unittest.mock import Mock, patch

from src.clients.odds_api_client import (
    OddsApiClient,
    OddsApiError,
    RateLimitError,
)


@pytest.fixture
def client():
    """Create an odds API client for testing."""
    return OddsApiClient(api_key='test_key', request_delay=0)


class TestOddsApiClientInitialization:
    """Test client initialization."""

    def test_init_with_valid_key(self):
        """Test initialization with valid API key."""
        client = OddsApiClient('test_key')
        assert client.api_key == 'test_key'
        assert client.session is not None

    def test_init_with_empty_key(self):
        """Test initialization with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            OddsApiClient('')

    def test_init_with_none_key(self):
        """Test initialization with None API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            OddsApiClient(None)

    def test_session_headers(self):
        """Test that session headers are set correctly."""
        client = OddsApiClient('test_key')
        assert 'X-RapidAPI-Key' in client.session.headers
        assert client.session.headers['X-RapidAPI-Key'] == 'test_key'
        assert client.session.headers['X-RapidAPI-Host'] == OddsApiClient.RAPIDAPI_HOST


class TestOddsApiClientLeagueMapping:
    """Test league ID mapping."""

    def test_league_id_mapping(self):
        """Test that league codes map to correct IDs."""
        assert OddsApiClient.LEAGUE_IDS['EPL'] == 'soccer_epl'
        assert OddsApiClient.LEAGUE_IDS['LA_LIGA'] == 'soccer_spain_la_liga'
        assert OddsApiClient.LEAGUE_IDS['SERIE_A'] == 'soccer_italy_serie_a'
        assert OddsApiClient.LEAGUE_IDS['BUNDESLIGA'] == 'soccer_germany_bundesliga'
        assert OddsApiClient.LEAGUE_IDS['LIGUE_1'] == 'soccer_france_ligue_one'

    def test_sport_ids(self):
        """Test sport ID mappings."""
        assert OddsApiClient.SPORT_IDS['soccer'] == 'soccer'
        assert OddsApiClient.SPORT_IDS['football'] == 'soccer'


class TestOddsApiClientRateLimiting:
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


class TestOddsApiClientAPIRequests:
    """Test API request handling."""

    @patch('src.clients.odds_api_client.requests.Session.get')
    def test_get_request_success(self, mock_get, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [{'id': 1, 'home_team': 'Team A'}]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = client._get('/odds')
        assert 'data' in result

    @patch('src.clients.odds_api_client.requests.Session.get')
    def test_get_request_rate_limit(self, mock_get, client):
        """Test API request with rate limit response."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError):
            client._get('/odds')

    @patch('src.clients.odds_api_client.requests.Session.get')
    def test_get_request_bad_request(self, mock_get, client):
        """Test API request with bad request response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'errors': ['Bad request']}
        mock_response.text = 'Bad request'
        mock_get.return_value = mock_response

        with pytest.raises(OddsApiError, match="Bad request"):
            client._get('/odds')

    @patch('src.clients.odds_api_client.requests.Session.get')
    def test_get_request_api_error(self, mock_get, client):
        """Test API request with API-level error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'errors': {'limit': 'Rate limit exceeded'},
        }
        mock_get.return_value = mock_response

        with pytest.raises(OddsApiError, match="API error"):
            client._get('/odds')

    @patch('src.clients.odds_api_client.requests.Session.get')
    def test_get_request_timeout(self, mock_get, client):
        """Test API request timeout."""
        import requests
        mock_get.side_effect = requests.Timeout()

        with pytest.raises(OddsApiError, match="Request timeout"):
            client._get('/odds')


class TestOddsApiClientSports:
    """Test sports-related API methods."""

    @patch.object(OddsApiClient, '_get')
    def test_get_sports(self, mock_get, client):
        """Test getting available sports."""
        mock_get.return_value = [
            {'key': 'soccer', 'title': 'Soccer', 'description': 'Football'},
            {'key': 'basketball', 'title': 'Basketball'},
        ]

        result = client.get_sports()
        assert len(result) == 2
        assert result[0]['key'] == 'soccer'

    @patch.object(OddsApiClient, '_get')
    def test_get_leagues(self, mock_get, client):
        """Test getting available leagues."""
        mock_get.return_value = [
            {'key': 'soccer_epl', 'title': 'English Premier League'},
            {'key': 'soccer_spain_la_liga', 'title': 'La Liga'},
            {'key': 'basketball_nba', 'title': 'NBA'},
        ]

        result = client.get_leagues()
        assert len(result) == 2  # Only soccer leagues
        assert result[0]['key'] == 'soccer_epl'


class TestOddsApiClientOdds:
    """Test odds-related API methods."""

    @patch.object(OddsApiClient, '_get')
    def test_get_odds(self, mock_get, client):
        """Test getting odds for a league."""
        mock_get.return_value = [
            {
                'id': 1,
                'home_team': 'Team A',
                'away_team': 'Team B',
                'bookmakers': [
                    {
                        'title': 'Bet365',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Team A', 'price': 2.50},
                                    {'name': 'Draw', 'price': 3.00},
                                    {'name': 'Team B', 'price': 2.75},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

        result = client.get_odds('soccer_epl')
        assert len(result) == 1
        assert result[0]['home_team'] == 'Team A'

    @patch.object(OddsApiClient, '_get')
    def test_get_odds_with_bookmakers(self, mock_get, client):
        """Test getting odds with bookmaker filter."""
        mock_get.return_value = []

        client.get_odds('soccer_epl', bookmakers=['bet365', 'draftkings'])
        mock_get.assert_called_once()

    @patch.object(OddsApiClient, '_get')
    def test_get_odds_with_markets(self, mock_get, client):
        """Test getting odds with market filter."""
        mock_get.return_value = []

        client.get_odds('soccer_epl', markets=['h2h', 'spreads'])
        mock_get.assert_called_once()

    @patch.object(OddsApiClient, '_get')
    def test_get_odds_for_league_code(self, mock_get, client):
        """Test getting odds using league code."""
        mock_get.return_value = []

        client.get_odds_for_league_code('EPL')
        mock_get.assert_called_once()

    @patch.object(OddsApiClient, '_get')
    def test_get_odds_for_league_code_unknown(self, mock_get, client):
        """Test getting odds with unknown league code."""
        with pytest.raises(OddsApiError, match="Unknown league code"):
            client.get_odds_for_league_code('UNKNOWN_LEAGUE')


class TestOddsApiClientHistorical:
    """Test historical odds queries."""

    @patch.object(OddsApiClient, '_get')
    def test_get_historical_odds(self, mock_get, client):
        """Test getting historical odds."""
        mock_get.return_value = [
            {'id': 1, 'home_team': 'Team A', 'away_team': 'Team B'},
            {'id': 2, 'home_team': 'Team C', 'away_team': 'Team D'},
        ]

        result = client.get_historical_odds('soccer_epl', '2023-08-12')
        assert len(result) == 2

    @patch.object(OddsApiClient, '_get')
    def test_get_historical_odds_with_bookmakers(self, mock_get, client):
        """Test historical odds with bookmaker filter."""
        mock_get.return_value = []

        client.get_historical_odds('soccer_epl', '2023-08-12', bookmakers=['bet365'])
        mock_get.assert_called_once()


class TestOddsApiClientBookmakers:
    """Test bookmaker-related API methods."""

    @patch.object(OddsApiClient, '_get')
    def test_get_bookmakers(self, mock_get, client):
        """Test getting available bookmakers."""
        mock_get.return_value = [
            'bet365',
            'draftkings',
            'fanduel',
            'betmgm',
        ]

        result = client.get_bookmakers()
        assert len(result) == 4
        assert 'bet365' in result


class TestOddsApiClientEventOdds:
    """Test event/match odds queries."""

    @patch.object(OddsApiClient, '_get')
    def test_get_event_odds(self, mock_get, client):
        """Test getting odds for a specific event."""
        mock_get.return_value = {
            'id': 'event_123',
            'home_team': 'Team A',
            'away_team': 'Team B',
            'bookmakers': [
                {
                    'title': 'Bet365',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'Team A', 'price': 2.50},
                                {'name': 'Draw', 'price': 3.00},
                                {'name': 'Team B', 'price': 2.75},
                            ]
                        }
                    ]
                }
            ]
        }

        result = client.get_event_odds('soccer_epl', 'event_123')
        assert result['id'] == 'event_123'

    @patch.object(OddsApiClient, '_get')
    def test_get_event_odds_with_bookmakers(self, mock_get, client):
        """Test event odds with bookmaker filter."""
        mock_get.return_value = {}

        client.get_event_odds('soccer_epl', 'event_123', bookmakers=['bet365'])
        mock_get.assert_called_once()


class TestOddsApiClientParsing:
    """Test odds parsing functionality."""

    def test_parse_odds_response(self, client):
        """Test parsing odds response."""
        raw_odds = {
            'id': 'match_1',
            'sport_key': 'soccer_epl',
            'sport_title': 'Premier League',
            'home_team': 'Manchester United',
            'away_team': 'Liverpool',
            'commence_time': '2023-08-12T15:00:00Z',
            'bookmakers': [
                {
                    'title': 'Bet365',
                    'last_update': '2023-08-12T10:00:00Z',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'Manchester United', 'price': 2.50},
                                {'name': 'Draw', 'price': 3.00},
                                {'name': 'Liverpool', 'price': 2.75},
                            ]
                        }
                    ]
                }
            ]
        }

        parsed = client.parse_odds_response(raw_odds)
        assert parsed['id'] == 'match_1'
        assert parsed['home_team'] == 'Manchester United'
        assert len(parsed['bookmakers']) == 1
        assert parsed['bookmakers'][0]['name'] == 'Bet365'

    def test_parse_odds_response_multiple_bookmakers(self, client):
        """Test parsing odds with multiple bookmakers."""
        raw_odds = {
            'id': 'match_1',
            'home_team': 'Team A',
            'away_team': 'Team B',
            'bookmakers': [
                {
                    'title': 'Bet365',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'Team A', 'price': 2.50},
                                {'name': 'Draw', 'price': 3.00},
                                {'name': 'Team B', 'price': 2.75},
                            ]
                        }
                    ]
                },
                {
                    'title': 'DraftKings',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'Team A', 'price': 2.45},
                                {'name': 'Draw', 'price': 3.10},
                                {'name': 'Team B', 'price': 2.80},
                            ]
                        }
                    ]
                }
            ]
        }

        parsed = client.parse_odds_response(raw_odds)
        assert len(parsed['bookmakers']) == 2


class TestOddsApiClientBestOdds:
    """Test best odds finding functionality."""

    def test_get_best_odds(self, client):
        """Test getting best odds across bookmakers."""
        parsed_odds = {
            'id': 'match_1',
            'bookmakers': [
                {
                    'name': 'Bet365',
                    'markets': {'home_win_odds': 2.50}
                },
                {
                    'name': 'DraftKings',
                    'markets': {'home_win_odds': 2.60}
                },
                {
                    'name': 'FanDuel',
                    'markets': {'home_win_odds': 2.55}
                }
            ]
        }

        best_odds = client.get_best_odds(parsed_odds, 'home_win')
        assert best_odds == 2.60

    def test_get_best_odds_not_found(self, client):
        """Test getting best odds when outcome not found."""
        parsed_odds = {
            'id': 'match_1',
            'bookmakers': [
                {
                    'name': 'Bet365',
                    'markets': {'home_win_odds': 2.50}
                }
            ]
        }

        best_odds = client.get_best_odds(parsed_odds, 'nonexistent')
        assert best_odds is None

    def test_get_best_odds_empty_bookmakers(self, client):
        """Test getting best odds with no bookmakers."""
        parsed_odds = {
            'id': 'match_1',
            'bookmakers': []
        }

        best_odds = client.get_best_odds(parsed_odds, 'home_win')
        assert best_odds is None
