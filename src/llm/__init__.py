"""SUT backends: fixture (offline) and live agent (import live submodule directly)."""

from src.llm.cases import (
    CaseValidationError,
    get_case_by_id,
    load_fixture_cases,
    suite_stats,
    validate_case,
)
from src.llm.fixture import FixtureSUT, FixtureSUTError, run_fixture_case

# Note: import LiveAgentSUT from src.llm.live to avoid circular imports
# (live → agent.loop → llm.client → llm package init).

__all__ = [
    "CaseValidationError",
    "FixtureSUT",
    "FixtureSUTError",
    "get_case_by_id",
    "load_fixture_cases",
    "run_fixture_case",
    "suite_stats",
    "validate_case",
]
