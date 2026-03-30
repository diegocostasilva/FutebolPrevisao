"""
ExecutionContext — the universal communication contract between Airflow, Agents, and Skills.

Rules (from PRD_ORIENTACAO_AGENTE_IA.md):
  - Context is the ONLY mechanism for passing state between layers.
  - No Skill may read configuration from outside the Context.
  - Artifacts produced by a Skill are stored in context.artifacts and consumed
    by subsequent Skills in the same Agent execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExecutionContext:
    """
    Carries identification, connections, parameters and inter-Skill artifacts
    for a single pipeline execution.

    Lifecycle:
        Created by the Airflow task callable → passed to Agent.execute()
        → forwarded unchanged to every Skill.validate() and Skill.execute().

    Attributes:
        run_id:            Airflow run_id (or generated UUID for manual runs).
        execution_date:    Logical execution date of the DAG run.
        dag_id:            DAG identifier (e.g. "football_daily_pipeline").
        task_id:           Task identifier within the DAG.
        environment:       "dev" | "staging" | "prod".

        spark_session:     Active SparkSession (injected by Databricks/Spark Skills).
        pg_connection:     Active psycopg2 connection (injected by Serving Skills).
        databricks_token:  Databricks personal access token.
        databricks_host:   Databricks workspace URL.
        api_football_key:  API-Football authentication key.

        params:            Runtime parameters from Airflow Variables / DAG conf.
                           Standard keys: league_ids, season, from_date, to_date, mode.
        artifacts:         Inter-Skill state within one Agent execution.
                           Skills WRITE here (e.g. fixture_ids, trained_model).
                           Subsequent Skills READ from here.
    """

    # ── Identity ───────────────────────────────────────────────────────────────
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_date: datetime = field(default_factory=datetime.utcnow)
    dag_id: str = ""
    task_id: str = ""
    environment: str = "dev"

    # ── Connections (injected at runtime, not serialised) ──────────────────────
    spark_session: Any | None = field(default=None, repr=False)
    pg_connection: Any | None = field(default=None, repr=False)
    databricks_token: str = field(default="", repr=False)
    databricks_host: str = ""
    databricks_http_path: str = ""  # /sql/1.0/warehouses/<id>
    api_football_key: str = field(default="", repr=False)

    # ── Dynamic data ──────────────────────────────────────────────────────────
    params: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        """True only when running in the production environment."""
        return self.environment == "prod"

    @property
    def league_ids(self) -> list[int]:
        """
        List of API-Football league IDs to process.
        Defaults to [71] (Brasileirão Série A) when not specified in params.
        """
        return self.params.get("league_ids", [71])

    @property
    def season(self) -> int:
        """Current season year. Defaults to 2025."""
        return self.params.get("season", 2025)

    @property
    def mode(self) -> str:
        """Execution mode: 'incremental' (default) or 'backfill'."""
        return self.params.get("mode", "incremental")

    # ── Convenience methods ───────────────────────────────────────────────────

    def set_artifact(self, key: str, value: Any) -> None:
        """Store a value in artifacts for consumption by subsequent Skills."""
        self.artifacts[key] = value

    def get_artifact(self, key: str, default: Any = None) -> Any:
        """Retrieve an artifact set by a previous Skill."""
        return self.artifacts.get(key, default)

    def __str__(self) -> str:
        return (
            f"ExecutionContext("
            f"run_id={self.run_id[:8]}…, "
            f"dag={self.dag_id}, "
            f"task={self.task_id}, "
            f"env={self.environment}, "
            f"leagues={self.league_ids}, "
            f"season={self.season}"
            f")"
        )
