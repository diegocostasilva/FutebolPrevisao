"""
FootballProcessingAgent — orquestra Bronze → Silver via jobs no cluster Databricks.

Cada Skill submete um notebook run no Databricks e aguarda conclusão.
O Airflow gerencia QUANDO o agent executa (via PythonOperator).
O Databricks gerencia COMO processa (Spark no cluster).

Ordem de execução:
    1. DatabricksFixturesFlatten    → silver.football_fixtures
    2. DatabricksStatisticsFlatten  → silver.football_match_statistics
    3. DatabricksEventsNormalize    → silver.football_match_events
    4. DatabricksOddsNormalize      → silver.football_odds_prematch
    5. DatabricksStandingsFlatten   → silver.football_standings
    6. DatabricksOptimize           → OPTIMIZE + ZORDER em todas as tabelas Silver
"""

from __future__ import annotations

from src.skills.processing import (
    DatabricksEventsNormalize,
    DatabricksFixturesFlatten,
    DatabricksOddsNormalize,
    DatabricksOptimize,
    DatabricksStandingsFlatten,
    DatabricksStatisticsFlatten,
)

from .base_agent import BaseAgent


class FootballProcessingAgent(BaseAgent):
    """
    Agent de processamento: dispara notebooks Databricks para transformar
    dados Bronze → Silver. Requer databricks_host e databricks_token no contexto.
    """

    def __init__(self) -> None:
        super().__init__(
            skills=[
                DatabricksFixturesFlatten(),
                DatabricksStatisticsFlatten(),
                DatabricksEventsNormalize(),
                DatabricksOddsNormalize(),
                DatabricksStandingsFlatten(),
                DatabricksOptimize(),
            ],
            max_retries=2,
        )
