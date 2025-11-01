"""
Unit tests for the data pipeline module.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.scraper.pipeline import DataPipeline, PipelineError
from src.db.models import League, Team, Match, MatchStatus


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def pipeline(mock_db_session):
    """Create a data pipeline instance with mocked components."""
    return DataPipeline(
        db_session=mock_db_session,
        football_data_key='test_fd_key',
        api_football_key='test_af_key',
    )


class TestPipelineInitialization:
    """Test pipeline initialization."""

    def test_init_with_all_keys(self, mock_db_session):
        """Test initialization with all API keys."""
        pipeline = DataPipeline(
            db_session=mock_db_session,
            football_data_key='fd_key',
            api_football_key='af_key',
        )
        assert pipeline.db is not None
        assert pipeline.fbref is not None
        assert pipeline.football_data is not None
        assert pipeline.api_football is not None

    def test_init_without_optional_keys(self, mock_db_session):
        """Test initialization without optional API keys."""
        pipeline = DataPipeline(db_session=mock_db_session)
        assert pipeline.db is not None
        assert pipeline.fbref is not None
        assert pipeline.football_data is None
        assert pipeline.api_football is None


class TestPipelineLeagueTransformation:
    """Test league data transformation."""

    def test_transform_to_league_epl(self, pipeline):
        """Test transforming EPL league data."""
        league = pipeline.transform_to_league('EPL', '2023-24')
        assert league.name == 'Premier League'
        assert league.country == 'England'
        assert league.season == '2023-24'
        assert league.external_id == 'EPL'

    def test_transform_to_league_la_liga(self, pipeline):
        """Test transforming La Liga data."""
        league = pipeline.transform_to_league('LA_LIGA', '2023-24')
        assert league.name == 'La Liga'
        assert league.country == 'Spain'

    def test_transform_to_league_unknown(self, pipeline):
        """Test transforming unknown league code."""
        with pytest.raises(PipelineError, match="Unknown league code"):
            pipeline.transform_to_league('UNKNOWN', '2023-24')


class TestPipelineTeamTransformation:
    """Test team data transformation."""

    def test_transform_to_team_dict_format(self, pipeline):
        """Test transforming team data from dictionary."""
        league = Mock(spec=League)
        league.id = 1
        league.country = 'England'

        team_data = {'name': 'Manchester United', 'id': 1}
        team = pipeline.transform_to_team(team_data, league)

        assert team.name == 'Manchester United'
        assert team.country == 'England'
        assert team.league_id == 1

    def test_transform_to_team_api_football_format(self, pipeline):
        """Test transforming team data from api-football format."""
        league = Mock(spec=League)
        league.id = 1
        league.country = 'England'

        team_data = {'team': {'name': 'Liverpool', 'id': 2}}
        team = pipeline.transform_to_team(team_data, league)

        assert team.name == 'Liverpool'

    def test_transform_to_team_string_format(self, pipeline):
        """Test transforming team data from string."""
        league = Mock(spec=League)
        league.id = 1
        league.country = 'England'

        team = pipeline.transform_to_team('Arsenal', league)
        assert team.name == 'Arsenal'


class TestPipelineMatchTransformation:
    """Test match data transformation."""

    def test_transform_to_match_success(self, pipeline):
        """Test transforming match data."""
        league = Mock(spec=League)
        league.id = 1

        home_team = Mock(spec=Team)
        home_team.id = 1

        away_team = Mock(spec=Team)
        away_team.id = 2

        match_data = {
            'id': 123,
            'utcDate': '2023-08-12T15:00:00Z',
            'status': 'FINISHED',
            'score': {'fullTime': {'home': 2, 'away': 1}},
        }

        match = pipeline.transform_to_match(
            match_data,
            league,
            home_team,
            away_team,
        )

        assert match.home_goals == 2
        assert match.away_goals == 1
        assert match.status == MatchStatus.FINISHED
        assert match.external_id == '123'

    def test_transform_to_match_status_mapping(self, pipeline):
        """Test status mapping in match transformation."""
        league = Mock(spec=League)
        league.id = 1
        home_team = Mock(spec=Team)
        home_team.id = 1
        away_team = Mock(spec=Team)
        away_team.id = 2

        statuses = [
            ('SCHEDULED', MatchStatus.SCHEDULED),
            ('LIVE', MatchStatus.LIVE),
            ('FINISHED', MatchStatus.FINISHED),
            ('POSTPONED', MatchStatus.POSTPONED),
            ('CANCELLED', MatchStatus.CANCELLED),
        ]

        for status_str, expected_status in statuses:
            match_data = {
                'id': 1,
                'utcDate': '2023-08-12T15:00:00Z',
                'status': status_str,
                'score': {'fullTime': {'home': None, 'away': None}},
            }
            match = pipeline.transform_to_match(match_data, league, home_team, away_team)
            assert match.status == expected_status


class TestPipelineMatchStatsStorage:
    """Test match statistics storage."""

    def test_store_match_stats(self, pipeline):
        """Test storing match statistics."""
        match = Mock(spec=Match)
        match.id = 1

        stats_data = {'shots': 15, 'possession': 55}
        match_stats = pipeline.store_match_stats(match, stats_data, 'fbref')

        assert match_stats.match_id == 1
        assert match_stats.source == 'fbref'
        assert 'shots' in match_stats.data_json


class TestPipelineDataFetching:
    """Test data fetching from sources."""

    @patch.object(DataPipeline, 'transform_to_league')
    @patch.object(DataPipeline, 'insert_or_update_league')
    def test_fetch_league_data_success(self, mock_insert, mock_transform, pipeline):
        """Test successful league data fetching."""
        mock_transform.return_value = Mock(spec=League)
        mock_insert.return_value = Mock(spec=League)

        with patch.object(pipeline.fbref, 'scrape_league_standings') as mock_scrape:
            mock_scrape.return_value = [{'name': 'Team A'}, {'name': 'Team B'}]

            result = pipeline.fetch_league_data('EPL', '2023-24', sources=['fbref'])

            assert result['league_code'] == 'EPL'
            assert result['season'] == '2023-24'
            assert len(result['standings']) == 2

    @patch.object(DataPipeline, 'insert_or_update_league')
    def test_fetch_league_data_no_sources(self, mock_insert, pipeline):
        """Test fetching league data with no available sources."""
        mock_insert.return_value = Mock(spec=League)

        with pytest.raises(PipelineError):
            pipeline.fetch_league_data('EPL', '2023-24', sources=[])


class TestPipelineInsertOrUpdate:
    """Test insert or update operations."""

    def test_insert_or_update_league_new(self, pipeline):
        """Test inserting new league."""
        pipeline.db.query().filter().first.return_value = None

        league = pipeline.insert_or_update_league('EPL', '2023-24')
        assert league.name == 'Premier League'
        pipeline.db.add.assert_called()
        pipeline.db.commit.assert_called()

    def test_insert_or_update_league_existing(self, pipeline):
        """Test updating existing league."""
        existing_league = Mock(spec=League)
        pipeline.db.query().filter().first.return_value = existing_league

        league = pipeline.insert_or_update_league('EPL', '2023-24')
        assert league == existing_league
        pipeline.db.add.assert_not_called()

    def test_insert_or_update_teams_new(self, pipeline):
        """Test inserting new teams."""
        league = Mock(spec=League)
        league.id = 1

        pipeline.db.query().filter().first.return_value = None

        teams_data = [{'name': 'Team A', 'id': 1}]
        teams = pipeline.insert_or_update_teams(league, teams_data)

        assert len(teams) > 0
        pipeline.db.add.assert_called()

    def test_insert_or_update_teams_existing(self, pipeline):
        """Test updating existing teams."""
        league = Mock(spec=League)
        league.id = 1

        existing_team = Mock(spec=Team)
        existing_team.name = 'Team A'
        pipeline.db.query().filter().first.return_value = existing_team

        teams_data = [{'name': 'Team A', 'id': 1}]
        teams = pipeline.insert_or_update_teams(league, teams_data)

        assert teams[0] == existing_team


class TestPipelineFullPipeline:
    """Test complete pipeline execution."""

    @patch.object(DataPipeline, 'fetch_league_data')
    @patch.object(DataPipeline, 'fetch_matches')
    @patch.object(DataPipeline, 'insert_or_update_league')
    @patch.object(DataPipeline, 'insert_or_update_teams')
    @patch.object(DataPipeline, 'insert_or_update_matches')
    def test_run_full_pipeline_success(
        self,
        mock_matches,
        mock_teams,
        mock_league,
        mock_fetch_matches,
        mock_fetch_league,
        pipeline,
    ):
        """Test running full pipeline."""
        league = Mock(spec=League)
        league.id = 1
        mock_league.return_value = league

        teams = [Mock(spec=Team), Mock(spec=Team)]
        mock_teams.return_value = teams

        matches = [Mock(spec=Match)]
        mock_matches.return_value = matches

        mock_fetch_league.return_value = {
            'league_code': 'EPL',
            'season': '2023-24',
            'standings': [{'name': 'Team A'}],
            'errors': [],
        }

        mock_fetch_matches.return_value = [{'id': 1}]

        result = pipeline.run_full_pipeline('EPL', '2023-24', fetch_matches=True)

        assert result['league_code'] == 'EPL'
        assert result['league_created'] is True
        assert result['teams_created'] == 2
        assert result['matches_created'] == 1
