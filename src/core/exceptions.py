"""
Custom exceptions for the MCP Agent DAG Platform.

Hierarchy:
    MCPSkillError
    ├── MCPValidationError    — precondition failed before execute()
    ├── MCPExecutionError     — failure during execute()
    ├── MCPQuotaExceededError — API-Football quota exhausted
    └── MCPDataLeakageError   — feature uses data posterior to match date
"""


class MCPSkillError(Exception):
    """Base exception for all MCP Skill errors."""

    def __init__(self, message: str, skill_name: str = "", skill_version: str = "") -> None:
        super().__init__(message)
        self.skill_name = skill_name
        self.skill_version = skill_version

    def __str__(self) -> str:
        prefix = f"[{self.skill_name} v{self.skill_version}] " if self.skill_name else ""
        return f"{prefix}{super().__str__()}"


class MCPValidationError(MCPSkillError):
    """Raised when a Skill's validate() detects missing or invalid preconditions."""


class MCPExecutionError(MCPSkillError):
    """Raised when a Skill's execute() fails after all retries are exhausted."""


class MCPQuotaExceededError(MCPSkillError):
    """
    Raised when API-Football quota (x-ratelimit-requests-remaining) reaches zero.
    The pipeline should halt ingestion and notify the team.
    """

    def __init__(
        self,
        message: str,
        remaining: int = 0,
        limit: int = 0,
        skill_name: str = "",
        skill_version: str = "",
    ) -> None:
        super().__init__(message, skill_name, skill_version)
        self.remaining = remaining
        self.limit = limit


class MCPDataLeakageError(MCPSkillError):
    """
    Raised when a feature computation detects data from after the match date.
    Prevents training contamination — all features must be available BEFORE the match.
    """

    def __init__(
        self,
        message: str,
        feature_name: str = "",
        fixture_id: int = 0,
        skill_name: str = "",
        skill_version: str = "",
    ) -> None:
        super().__init__(message, skill_name, skill_version)
        self.feature_name = feature_name
        self.fixture_id = fixture_id
