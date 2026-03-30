"""
MCPSkill — abstract base class for every unit of work in the platform.

Contract (from PRD_ORIENTACAO_AGENTE_IA.md):
  - Skills are STATELESS: all required information comes via ExecutionContext.
  - validate() runs BEFORE execute() — must raise MCPValidationError on any
    missing precondition. Never let execute() guess about bad inputs.
  - execute() returns a SkillResult — never raises, never returns None.
  - rollback() is optional but REQUIRED for any Skill that mutates data
    (INSERT, UPDATE, DELETE, MERGE).
  - name follows the pattern domain_action (e.g. spark_bronze_to_silver).
  - version follows semantic versioning. Breaking changes increment major.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .context import ExecutionContext
from .exceptions import MCPValidationError
from .result import SkillResult


class MCPSkill(ABC):
    """
    Abstract base for all MCP Skills.

    Subclass and implement: name, version, validate(), execute().
    Optionally override rollback() for data-mutating Skills.
    """

    # ── Identity (implemented as class-level properties) ──────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this Skill.
        Convention: domain_action  (e.g. 'api_football_fixtures_extractor',
                                         'spark_football_fixtures_flatten',
                                         'postgres_predictions_upsert')
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Semantic version string (e.g. '1.0.0').
        Increment MAJOR on breaking interface changes.
        """

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @abstractmethod
    def validate(self, context: ExecutionContext) -> bool:
        """
        Verify ALL preconditions before execute() runs.

        Must raise MCPValidationError (not return False) when a required
        input is missing or invalid. This ensures fail-fast behaviour and
        prevents execute() from running with incomplete state.

        Returns:
            True if all preconditions are satisfied.

        Raises:
            MCPValidationError: if any precondition fails.
        """

    @abstractmethod
    def execute(self, context: ExecutionContext) -> SkillResult:
        """
        Perform the Skill's atomic unit of work.

        Rules:
          - Called only after validate() returns True.
          - Must return a SkillResult (use SkillResult.ok() / SkillResult.fail()).
          - Must NOT raise exceptions — catch internally and return SkillResult.fail().
          - Must write produced state to context.artifacts for downstream Skills.

        Args:
            context: The shared ExecutionContext for this pipeline run.

        Returns:
            SkillResult with success=True on completion, success=False on error.
        """

    def rollback(self, context: ExecutionContext) -> None:
        """
        Undo mutations performed by execute() in case of downstream failure.

        Override this in any Skill that writes to Bronze, Silver, Gold,
        or PostgreSQL. The default implementation is a no-op (safe for
        read-only Skills).

        Called by BaseAgent.execute() when fail-fast triggers.
        """

    # ── String representation ─────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, version={self.version!r})"

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"
