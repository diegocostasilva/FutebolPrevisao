"""
FootballIngestionAgent — orquestra todas as Skills de ingestão da API-Football.

Ordem de execução (conforme PRD):
    1.  LeaguesExtractor       → metadados e coverage das ligas
    2.  FixturesExtractor      → partidas → gera fixture_ids nos artifacts
    3.  StatisticsExtractor    → estatísticas por fixture
    4.  EventsExtractor        → gols, cartões, substituições
    5.  LineupsExtractor       → escalações
    6.  PlayersExtractor       → stats de jogadores
    7.  OddsExtractor          → odds pré-jogo (1X2, O/U, BTTS)
    8.  StandingsExtractor     → classificação
    9.  InjuriesExtractor      → lesões
    10. PredictionsExtractor   → predições da API (features para ML)
    11. TeamsExtractor         → dados cadastrais de times
    12. QuotaMonitor           → relatório de consumo de quota

max_retries=3 porque a API pode ter instabilidade pontual.
"""

from __future__ import annotations

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

from .base_agent import BaseAgent


class FootballIngestionAgent(BaseAgent):
    """
    Agent de ingestão: coleta dados da API-Football e persiste na Bronze.

    Instancia as Skills na ordem correta — FixturesExtractor deve rodar antes
    das Skills que dependem de fixture_ids nos artifacts.
    """

    def __init__(self) -> None:
        super().__init__(
            skills=[
                APIFootballLeaguesExtractor(),
                APIFootballFixturesExtractor(),
                APIFootballStatisticsExtractor(),
                APIFootballEventsExtractor(),
                APIFootballLineupsExtractor(),
                APIFootballPlayersExtractor(),
                APIFootballOddsExtractor(),
                APIFootballStandingsExtractor(),
                APIFootballInjuriesExtractor(),
                APIFootballPredictionsExtractor(),
                APIFootballTeamsExtractor(),
                APIFootballQuotaMonitor(),
            ],
            max_retries=3,
        )
