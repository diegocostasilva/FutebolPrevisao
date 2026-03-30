"""Skills de ingestão da API-Football."""

from .api_football_base import APIFootballBaseSkill
from .api_football_events import APIFootballEventsExtractor
from .api_football_fixtures import APIFootballFixturesExtractor
from .api_football_injuries import APIFootballInjuriesExtractor
from .api_football_leagues import APIFootballLeaguesExtractor
from .api_football_lineups import APIFootballLineupsExtractor
from .api_football_odds import APIFootballOddsExtractor
from .api_football_players import APIFootballPlayersExtractor
from .api_football_predictions import APIFootballPredictionsExtractor
from .api_football_quota_monitor import APIFootballQuotaMonitor
from .api_football_standings import APIFootballStandingsExtractor
from .api_football_statistics import APIFootballStatisticsExtractor
from .api_football_teams import APIFootballTeamsExtractor

__all__ = [
    "APIFootballBaseSkill",
    "APIFootballLeaguesExtractor",
    "APIFootballFixturesExtractor",
    "APIFootballStatisticsExtractor",
    "APIFootballEventsExtractor",
    "APIFootballLineupsExtractor",
    "APIFootballPlayersExtractor",
    "APIFootballOddsExtractor",
    "APIFootballStandingsExtractor",
    "APIFootballInjuriesExtractor",
    "APIFootballPredictionsExtractor",
    "APIFootballTeamsExtractor",
    "APIFootballQuotaMonitor",
]
