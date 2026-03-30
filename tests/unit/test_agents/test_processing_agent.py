"""Testes para src/agents/football_processing_agent.py"""

from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.agents.football_processing_agent import FootballProcessingAgent
from src.skills.processing import (
    DatabricksEventsNormalize,
    DatabricksFixturesFlatten,
    DatabricksOddsNormalize,
    DatabricksOptimize,
    DatabricksStandingsFlatten,
    DatabricksStatisticsFlatten,
)


class TestFootballProcessingAgentConstruction:
    def test_is_base_agent(self):
        assert isinstance(FootballProcessingAgent(), BaseAgent)

    def test_has_6_skills(self):
        assert len(FootballProcessingAgent().skills) == 6

    def test_max_retries_is_2(self):
        assert FootballProcessingAgent().max_retries == 2

    def test_skill_order(self):
        names = [s.name for s in FootballProcessingAgent().skills]

        assert names[0] == "databricks_fixtures_flatten"
        assert names[1] == "databricks_statistics_flatten"
        assert names[2] == "databricks_events_normalize"
        assert names[3] == "databricks_odds_normalize"
        assert names[4] == "databricks_standings_flatten"
        assert names[5] == "databricks_optimize"

    def test_flatten_before_optimize(self):
        """Todos os flattens devem rodar antes do OPTIMIZE."""
        names = [s.name for s in FootballProcessingAgent().skills]
        optimize_idx = names.index("databricks_optimize")
        for flatten in [
            "databricks_fixtures_flatten",
            "databricks_statistics_flatten",
            "databricks_events_normalize",
        ]:
            assert names.index(flatten) < optimize_idx

    def test_all_required_skill_types_present(self):
        skill_types = {type(s) for s in FootballProcessingAgent().skills}

        assert DatabricksFixturesFlatten in skill_types
        assert DatabricksStatisticsFlatten in skill_types
        assert DatabricksEventsNormalize in skill_types
        assert DatabricksOddsNormalize in skill_types
        assert DatabricksStandingsFlatten in skill_types
        assert DatabricksOptimize in skill_types

    def test_all_skills_are_databricks_based(self):
        """Nenhuma skill deve executar Spark localmente."""
        from src.skills.processing.databricks_job_base import DatabricksJobBaseSkill

        for skill in FootballProcessingAgent().skills:
            assert isinstance(skill, DatabricksJobBaseSkill), (
                f"{skill.name} não herda de DatabricksJobBaseSkill"
            )
