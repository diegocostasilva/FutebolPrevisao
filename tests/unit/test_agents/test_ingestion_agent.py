"""Testes para src/agents/football_ingestion_agent.py"""

from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.agents.football_ingestion_agent import FootballIngestionAgent
from src.skills.ingestion import (
    APIFootballEventsExtractor,
    APIFootballFixturesExtractor,
    APIFootballInjuriesExtractor,
    APIFootballLeaguesExtractor,
    APIFootballLineupsExtractor,
    APIFootballOddsExtractor,
    APIFootballPlayersExtractor,
    APIFootballPredictionsExtractor,
    APIFootballQuotaMonitor,
    APIFootballStandingsExtractor,
    APIFootballStatisticsExtractor,
    APIFootballTeamsExtractor,
)


class TestFootballIngestionAgentConstruction:
    def test_is_base_agent(self):
        assert isinstance(FootballIngestionAgent(), BaseAgent)

    def test_max_retries_is_3(self):
        assert FootballIngestionAgent().max_retries == 3

    def test_has_12_skills(self):
        assert len(FootballIngestionAgent().skills) == 12

    def test_skill_order(self):
        skills = FootballIngestionAgent().skills
        names = [s.name for s in skills]

        assert names[0] == "api_football_leagues_extractor"
        assert names[1] == "api_football_fixtures_extractor"
        assert names[-1] == "api_football_quota_monitor"

    def test_fixtures_before_statistics(self):
        """FixturesExtractor deve rodar antes de StatisticsExtractor (gera fixture_ids)."""
        skills = FootballIngestionAgent().skills
        names = [s.name for s in skills]
        assert names.index("api_football_fixtures_extractor") < names.index(
            "api_football_statistics_extractor"
        )

    def test_all_required_skill_types_present(self):
        agent = FootballIngestionAgent()
        skill_types = {type(s) for s in agent.skills}

        assert APIFootballLeaguesExtractor in skill_types
        assert APIFootballFixturesExtractor in skill_types
        assert APIFootballStatisticsExtractor in skill_types
        assert APIFootballEventsExtractor in skill_types
        assert APIFootballLineupsExtractor in skill_types
        assert APIFootballPlayersExtractor in skill_types
        assert APIFootballOddsExtractor in skill_types
        assert APIFootballStandingsExtractor in skill_types
        assert APIFootballInjuriesExtractor in skill_types
        assert APIFootballPredictionsExtractor in skill_types
        assert APIFootballTeamsExtractor in skill_types
        assert APIFootballQuotaMonitor in skill_types
