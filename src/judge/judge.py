"""L3 judges — LLM evaluates agent tool trajectory."""

from __future__ import annotations

from typing import Any

from src.agent.types import AgentResult
from src.config.settings import Settings, get_settings
from src.judge.trajectory_judge import (
    TrajectoryJudgeVerdict,
    run_trajectory_judge,
)
from src.llm.client import OpenAICompatibleClient
from src.scoring.models import ScoreIssue


def run_judge(
    case: dict[str, Any],
    result: AgentResult,
    *,
    client: OpenAICompatibleClient | None = None,
    settings: Settings | None = None,
    threshold: int = 3,
) -> list[ScoreIssue]:
    """
    L3: LLM evaluates the agent TOOL TRAJECTORY.

    Honors JUDGE_ENABLED. Prefer judge_trajectory() for full verdict object.
    """
    settings = settings or get_settings()
    if not settings.judge_enabled:
        return []

    verdict = run_trajectory_judge(
        case,
        result,
        client=client,
        settings=settings,
        threshold=threshold,
    )
    return verdict.to_score_issues()


def judge_trajectory(
    case: dict[str, Any],
    result: AgentResult,
    *,
    client: OpenAICompatibleClient | None = None,
    settings: Settings | None = None,
    threshold: int = 3,
) -> TrajectoryJudgeVerdict:
    """Public alias for trajectory LLM review."""
    settings = settings or get_settings()
    return run_trajectory_judge(
        case,
        result,
        client=client,
        settings=settings,
        threshold=threshold,
    )
