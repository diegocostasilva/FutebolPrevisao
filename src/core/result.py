"""
Standardized return object for every MCP Skill execution.

Every Skill.execute() MUST return a SkillResult — never raw data or None.
This contract enables uniform logging, auditing, and rollback decisions by Agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResult:
    """
    Standardized return object for every MCP Skill execution.

    Attributes:
        success:       True if the Skill completed without errors.
        message:       Human-readable description of what happened.
        rows_affected: Number of records created, updated, or validated.
        data:          Optional metadata produced by the Skill (e.g. fixture_ids
                       collected, model_version registered). Consumed by
                       subsequent Skills via context.artifacts.
        error:         Captured exception, populated only on failure.
    """

    success: bool
    message: str
    rows_affected: int = 0
    data: dict[str, Any] | None = None
    error: Exception | None = field(default=None, repr=False)

    # ── Convenience constructors ───────────────────────────────────────────────

    @classmethod
    def ok(cls, message: str, rows_affected: int = 0, data: dict[str, Any] | None = None) -> "SkillResult":
        """Create a successful SkillResult."""
        return cls(success=True, message=message, rows_affected=rows_affected, data=data)

    @classmethod
    def fail(cls, message: str, error: Exception | None = None, rows_affected: int = 0) -> "SkillResult":
        """Create a failed SkillResult."""
        return cls(success=False, message=message, rows_affected=rows_affected, error=error)

    def __str__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return f"SkillResult[{status}] rows={self.rows_affected} | {self.message}"
