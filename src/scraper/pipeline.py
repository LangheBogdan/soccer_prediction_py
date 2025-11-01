"""
Data pipeline for orchestrating data collection from multiple sources.

This module provides functionality to:
1. Collect data from FBref, football-data.org, and api-football.com
2. Transform scraped data to ORM models
3. Insert/update data in the database
4. Handle data deduplication and conflicts
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.db.models import (
    League,
    Team,
    Match,
    TeamStats,
    MatchStats,
    MatchStatus,
    LeagueType,
)
from src.clients.football_data_client import FootballDataClient
from src.clients.api_football_client import ApiFootballClient
from src.clients.odds_api_client import OddsApiClient
from src.scraper.fbref_scraper import FbrefScraper

# Configure logging
logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class DataPipeline:
    """
    Orchestrates data collection, transformation, and storage.

    This pipeline:
    1. Fetches data from multiple sources (FBref, football-data.org, api-football.com)
    2. Transforms raw data to ORM models
    3. Handles data conflicts and deduplication
    4. Bulk inserts into database
    """

    def __init__(
        self,
        db_session: Session,
        football_data_key: Optional[str] = None,
        api_football_key: Optional[str] = None,
        odds_api_key: Optional[str] = None,
    ):
        """
        Initialize the data pipeline.

        Args:
            db_session: SQLAlchemy database session
            football_data_key: API key for football-data.org
            api_football_key: API key for api-football.com
            odds_api_key: API key for the-odds-api.com
        """
        self.db = db_session
        self.fbref = FbrefScraper()
        self.football_data = (
            FootballDataClient(football_data_key)
            if football_data_key
            else None
        )
        self.api_football = (
            ApiFootballClient(api_football_key)
            if api_football_key
            else None
        )
        self.odds_api = (
            OddsApiClient(odds_api_key)
            if odds_api_key
            else None
        )

    def fetch_league_data(
        self,
        league_code: str,
        season: str,
        sources: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch league data from multiple sources.

        Args:
            league_code: League code (e.g., 'EPL')
            season: Season (e.g., '2023-24')
            sources: List of sources to fetch from (['fbref', 'football_data', 'api_football'])

        Returns:
            Dictionary with aggregated data from all sources

        Raises:
            PipelineError: If no data can be fetched
        """
        if sources is None:
            sources = ['fbref', 'football_data', 'api_football']

        data = {
            'league_code': league_code,
            'season': season,
            'teams': {},
            'matches': [],
            'standings': [],
            'errors': [],
        }

        # Fetch from FBref
        if 'fbref' in sources:
            try:
                logger.info(f"Fetching FBref data for {league_code}...")
                standings = self.fbref.scrape_league_standings(league_code, season)
                data['standings'].extend(standings)
            except Exception as e:
                logger.error(f"FBref fetch failed: {e}")
                data['errors'].append(f"FBref: {str(e)}")

        # Fetch from football-data.org
        if 'football_data' in sources and self.football_data:
            try:
                logger.info(f"Fetching football-data.org data for {league_code}...")
                standings = self.football_data.get_standings(league_code)
                for team in standings:
                    if 'team' in team:
                        data['standings'].append(team['team'])
            except Exception as e:
                logger.error(f"football-data.org fetch failed: {e}")
                data['errors'].append(f"football-data.org: {str(e)}")

        # Fetch from api-football.com
        if 'api_football' in sources and self.api_football:
            try:
                logger.info(f"Fetching api-football.com data for {league_code}...")
                league_id = ApiFootballClient.LEAGUE_IDS.get(league_code)
                if league_id:
                    season_year = int(season.split('-')[0])
                    standings = self.api_football.get_league_standings(league_id, season_year)
                    data['standings'].extend(standings)
            except Exception as e:
                logger.error(f"api-football.com fetch failed: {e}")
                data['errors'].append(f"api-football.com: {str(e)}")

        if not data['standings']:
            raise PipelineError(f"Could not fetch any league data for {league_code}")

        logger.info(
            f"Fetched {len(data['standings'])} standings entries from "
            f"{len(sources)} sources"
        )
        return data

    def fetch_matches(
        self,
        league_code: str,
        season: str,
        status: str = 'SCHEDULED',
        sources: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch matches from multiple sources.

        Args:
            league_code: League code
            season: Season
            status: Match status filter
            sources: List of sources to fetch from

        Returns:
            List of match dictionaries

        Raises:
            PipelineError: If no data can be fetched
        """
        if sources is None:
            sources = ['football_data', 'api_football']

        matches = []

        # Fetch from football-data.org
        if 'football_data' in sources and self.football_data:
            try:
                logger.info(f"Fetching matches from football-data.org for {league_code}...")
                league_matches = self.football_data.get_current_matches(
                    league_code,
                    status=status
                )
                matches.extend(league_matches)
            except Exception as e:
                logger.error(f"football-data.org match fetch failed: {e}")

        # Fetch from api-football.com
        if 'api_football' in sources and self.api_football:
            try:
                logger.info(f"Fetching matches from api-football.com for {league_code}...")
                league_id = ApiFootballClient.LEAGUE_IDS.get(league_code)
                if league_id:
                    season_year = int(season.split('-')[0])
                    league_matches = self.api_football.get_fixtures(
                        league_id,
                        season_year,
                        status=status
                    )
                    matches.extend(league_matches)
            except Exception as e:
                logger.error(f"api-football.com match fetch failed: {e}")

        if not matches:
            raise PipelineError(f"Could not fetch matches for {league_code}")

        logger.info(f"Fetched {len(matches)} matches")
        return matches

    def transform_to_league(
        self,
        league_code: str,
        season: str,
        league_type: str = 'DOMESTIC',
    ) -> League:
        """
        Transform league data to ORM model.

        Args:
            league_code: League code
            season: Season
            league_type: Type of league

        Returns:
            League ORM model instance
        """
        # Map league code to full name and country
        league_info = {
            'EPL': {'name': 'Premier League', 'country': 'England'},
            'LA_LIGA': {'name': 'La Liga', 'country': 'Spain'},
            'SERIE_A': {'name': 'Serie A', 'country': 'Italy'},
            'BUNDESLIGA': {'name': 'Bundesliga', 'country': 'Germany'},
            'LIGUE_1': {'name': 'Ligue 1', 'country': 'France'},
        }

        if league_code not in league_info:
            raise PipelineError(f"Unknown league code: {league_code}")

        info = league_info[league_code]
        league = League(
            name=info['name'],
            country=info['country'],
            season=season,
            league_type=league_type,
            external_id=league_code,
        )

        return league

    def transform_to_team(
        self,
        team_data: Dict[str, Any],
        league: League,
    ) -> Team:
        """
        Transform team data to ORM model.

        Args:
            team_data: Raw team data
            league: Parent League instance

        Returns:
            Team ORM model instance
        """
        # Handle various data source formats
        if isinstance(team_data, dict):
            if 'team' in team_data:
                # api-football format
                team_info = team_data['team']
                name = team_info.get('name', '')
            elif 'name' in team_data:
                # fbref or football-data format
                name = team_data['name']
            else:
                name = str(team_data.get('id', 'Unknown'))
        else:
            name = str(team_data)

        team = Team(
            name=name,
            country=league.country,
            league_id=league.id,
            external_id=str(team_data.get('id', '')) if isinstance(team_data, dict) else None,
        )

        return team

    def transform_to_match(
        self,
        match_data: Dict[str, Any],
        league: League,
        home_team: Team,
        away_team: Team,
    ) -> Match:
        """
        Transform match data to ORM model.

        Args:
            match_data: Raw match data
            league: Parent League
            home_team: Home Team
            away_team: Away Team

        Returns:
            Match ORM model instance
        """
        # Parse date
        date_str = match_data.get('utcDate') or match_data.get('date')
        if isinstance(date_str, str):
            match_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            match_date = datetime.utcnow()

        # Map status
        status_str = match_data.get('status', 'SCHEDULED')
        status_map = {
            'SCHEDULED': MatchStatus.SCHEDULED,
            'LIVE': MatchStatus.LIVE,
            'FINISHED': MatchStatus.FINISHED,
            'POSTPONED': MatchStatus.POSTPONED,
            'CANCELLED': MatchStatus.CANCELLED,
        }
        status = status_map.get(status_str, MatchStatus.SCHEDULED)

        # Extract scores
        score = match_data.get('score', {})
        if isinstance(score, dict):
            home_goals = score.get('fullTime', {}).get('home')
            away_goals = score.get('fullTime', {}).get('away')
        else:
            home_goals = None
            away_goals = None

        match = Match(
            league_id=league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=match_date,
            home_goals=home_goals,
            away_goals=away_goals,
            status=status,
            external_id=str(match_data.get('id', '')),
        )

        return match

    def store_match_stats(
        self,
        match: Match,
        stats_data: Dict[str, Any],
        source: str,
    ) -> MatchStats:
        """
        Store match statistics from a data source.

        Args:
            match: Match instance
            stats_data: Statistics data
            source: Data source name

        Returns:
            MatchStats ORM model instance
        """
        import json

        match_stats = MatchStats(
            match_id=match.id,
            source=source,
            data_json=json.dumps(stats_data) if stats_data else None,
        )

        return match_stats

    def insert_or_update_league(
        self,
        league_code: str,
        season: str,
    ) -> League:
        """
        Insert or update league in database.

        Args:
            league_code: League code
            season: Season

        Returns:
            Existing or newly created League
        """
        existing = self.db.query(League).filter(
            League.external_id == league_code,
            League.season == season,
        ).first()

        if existing:
            logger.info(f"League {league_code} {season} already exists")
            return existing

        league = self.transform_to_league(league_code, season)
        try:
            self.db.add(league)
            self.db.commit()
            logger.info(f"Created league {league_code} {season}")
            return league
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create league: {e}")
            raise PipelineError(f"Failed to create league: {e}")

    def insert_or_update_teams(
        self,
        league: League,
        teams_data: List[Dict[str, Any]],
    ) -> List[Team]:
        """
        Insert or update teams in database.

        Args:
            league: Parent League
            teams_data: List of team data dictionaries

        Returns:
            List of Team instances (existing and new)
        """
        teams = []

        for team_data in teams_data:
            # Extract team name
            if isinstance(team_data, dict):
                team_name = team_data.get('name', '')
            else:
                team_name = str(team_data)

            if not team_name:
                continue

            # Check if team exists
            existing = self.db.query(Team).filter(
                Team.name == team_name,
                Team.league_id == league.id,
            ).first()

            if existing:
                teams.append(existing)
                continue

            # Create new team
            team = self.transform_to_team(team_data, league)
            try:
                self.db.add(team)
                self.db.commit()
                logger.debug(f"Created team {team_name}")
                teams.append(team)
            except IntegrityError as e:
                self.db.rollback()
                logger.warning(f"Failed to create team {team_name}: {e}")

        return teams

    def insert_or_update_matches(
        self,
        league: League,
        teams: List[Team],
        matches_data: List[Dict[str, Any]],
    ) -> List[Match]:
        """
        Insert or update matches in database.

        Args:
            league: Parent League
            teams: List of Team instances
            matches_data: List of match data dictionaries

        Returns:
            List of Match instances (existing and new)
        """
        matches = []
        team_dict = {team.name: team for team in teams}

        for match_data in matches_data:
            # Extract team names and find Team instances
            home_name = None
            away_name = None

            # Handle different data source formats
            if 'homeTeam' in match_data:
                home_name = match_data['homeTeam'].get('name', '')
            elif 'teams' in match_data:
                home_name = match_data['teams']['home'].get('name', '')

            if 'awayTeam' in match_data:
                away_name = match_data['awayTeam'].get('name', '')
            elif 'teams' in match_data:
                away_name = match_data['teams']['away'].get('name', '')

            if not home_name or not away_name:
                logger.warning(f"Could not extract team names from match data")
                continue

            # Find Team instances
            home_team = team_dict.get(home_name)
            away_team = team_dict.get(away_name)

            if not home_team or not away_team:
                logger.warning(
                    f"Could not find teams for match: {home_name} vs {away_name}"
                )
                continue

            # Check if match exists
            external_id = match_data.get('id')
            if external_id:
                existing = self.db.query(Match).filter(
                    Match.external_id == str(external_id)
                ).first()

                if existing:
                    matches.append(existing)
                    continue

            # Create new match
            try:
                match = self.transform_to_match(
                    match_data,
                    league,
                    home_team,
                    away_team,
                )
                self.db.add(match)
                self.db.commit()
                logger.debug(f"Created match {home_name} vs {away_name}")
                matches.append(match)
            except IntegrityError as e:
                self.db.rollback()
                logger.warning(f"Failed to create match: {e}")

        return matches

    def fetch_and_store_odds(
        self,
        league_code: str,
        match_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Fetch odds from the-odds-api.com and store in database.

        Args:
            league_code: League code (e.g., 'EPL', 'LA_LIGA')
            match_id: Specific match ID to fetch odds for (optional)

        Returns:
            Dictionary with fetch results and statistics

        Raises:
            PipelineError: If odds API client is not configured
        """
        from src.db.models import Odds

        if not self.odds_api:
            raise PipelineError("Odds API client not configured")

        result = {
            'league_code': league_code,
            'odds_fetched': 0,
            'odds_stored': 0,
            'errors': [],
        }

        try:
            # Get odds from API
            logger.info(f"Fetching odds for {league_code}")
            odds_data = self.odds_api.get_odds_for_league_code(league_code)

            if not odds_data:
                logger.warning(f"No odds data available for {league_code}")
                return result

            result['odds_fetched'] = len(odds_data)

            # Process each match's odds
            for match_odds in odds_data:
                try:
                    # Extract match information
                    home_team = match_odds.get('home_team')
                    away_team = match_odds.get('away_team')
                    commence_time = match_odds.get('commence_time')

                    # Find matching match in database
                    from src.db.models import Match
                    db_match = (
                        self.db.query(Match)
                        .join(Match.home_team_obj)
                        .join(Match.away_team_obj)
                        .filter(
                            Match.home_team_obj.has(name=home_team),
                            Match.away_team_obj.has(name=away_team),
                        )
                        .first()
                    )

                    if not db_match:
                        logger.debug(f"No match found for {home_team} vs {away_team}")
                        continue

                    # If specific match_id requested, filter
                    if match_id and db_match.id != match_id:
                        continue

                    # Store odds from each bookmaker
                    for bookmaker_data in match_odds.get('bookmakers', []):
                        try:
                            bookmaker_name = bookmaker_data.get('key')
                            markets = bookmaker_data.get('markets', [])

                            # Extract h2h (match winner) odds
                            h2h_market = next(
                                (m for m in markets if m.get('key') == 'h2h'),
                                None
                            )

                            if not h2h_market:
                                continue

                            outcomes = h2h_market.get('outcomes', [])

                            # Map outcomes to odds
                            home_odds = None
                            draw_odds = None
                            away_odds = None

                            for outcome in outcomes:
                                team_name = outcome.get('name')
                                odds_value = outcome.get('price')

                                if team_name == home_team:
                                    home_odds = odds_value
                                elif team_name == away_team:
                                    away_odds = odds_value
                                elif team_name.lower() == 'draw':
                                    draw_odds = odds_value

                            # Extract totals (over/under) if available
                            totals_market = next(
                                (m for m in markets if m.get('key') == 'totals'),
                                None
                            )

                            over_2_5 = None
                            under_2_5 = None

                            if totals_market:
                                for outcome in totals_market.get('outcomes', []):
                                    if outcome.get('name') == 'Over' and outcome.get('point') == 2.5:
                                        over_2_5 = outcome.get('price')
                                    elif outcome.get('name') == 'Under' and outcome.get('point') == 2.5:
                                        under_2_5 = outcome.get('price')

                            # Create or update odds record
                            odds_record = Odds(
                                match_id=db_match.id,
                                bookmaker=bookmaker_name,
                                home_win_odds=home_odds,
                                draw_odds=draw_odds,
                                away_win_odds=away_odds,
                                over_2_5_odds=over_2_5,
                                under_2_5_odds=under_2_5,
                                retrieved_at=datetime.utcnow(),
                            )

                            self.db.add(odds_record)
                            result['odds_stored'] += 1

                        except Exception as e:
                            logger.warning(f"Failed to store odds for bookmaker {bookmaker_name}: {e}")
                            result['errors'].append(str(e))

                except Exception as e:
                    logger.warning(f"Failed to process match odds: {e}")
                    result['errors'].append(str(e))

            # Commit all odds
            self.db.commit()
            logger.info(
                f"Stored {result['odds_stored']} odds records for {league_code}"
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to fetch/store odds: {e}")
            result['errors'].append(str(e))

        return result

    def run_full_pipeline(
        self,
        league_code: str,
        season: str,
        fetch_matches: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the complete data pipeline.

        Args:
            league_code: League code
            season: Season
            fetch_matches: Whether to fetch and store matches

        Returns:
            Pipeline result summary

        Raises:
            PipelineError: If critical pipeline step fails
        """
        result = {
            'league_code': league_code,
            'season': season,
            'league_created': False,
            'teams_created': 0,
            'matches_created': 0,
            'errors': [],
        }

        try:
            # Step 1: Fetch and create league
            logger.info(f"Starting pipeline for {league_code} {season}")
            league = self.insert_or_update_league(league_code, season)
            result['league_created'] = True

            # Step 2: Fetch league data
            league_data = self.fetch_league_data(league_code, season)
            result['errors'].extend(league_data['errors'])

            # Step 3: Create/update teams
            teams = self.insert_or_update_teams(league, league_data['standings'])
            result['teams_created'] = len(teams)

            # Step 4: Fetch and create matches
            if fetch_matches:
                matches_data = self.fetch_matches(league_code, season)
                matches = self.insert_or_update_matches(league, teams, matches_data)
                result['matches_created'] = len(matches)

            logger.info(
                f"Pipeline completed: {result['teams_created']} teams, "
                f"{result['matches_created']} matches"
            )

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            result['errors'].append(str(e))
            raise PipelineError(f"Pipeline failed: {e}")

        return result
