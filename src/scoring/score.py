"""Aggregate L1 + L2 + L3 (LLM trajectory judge) scoring entrypoint."""

from __future__ import annotations

from typing import Any

from src.agent.types import AgentResult
from src.scoring.config import load_scoring_config
from src.scoring.l1_trajectory import score_l1
from src.scoring.l2_answer import score_l2
from src.scoring.models import (
    LayerScore,
    ScoreResult,
    layer_status_from_issues,
    merge_verdict,
)
from src.scoring.taxonomy import classify_failure


def score_run(
    case: dict[str, Any],
    result: AgentResult,
    *,
    policy: dict[str, Any] | None = None,
    run_l3: bool | None = None,
) -> ScoreResult:
    """
    Score an agent run against case expectations.

    L1/L2 = deterministic path + answer gates (always).
    L3 = LLM trajectory judge when:
      - run_l3=True, or
      - run_l3=None (auto) and OPENAI_API_KEY is set and JUDGE_ENABLED is not false

    Offline CI should pass run_l3=False.
    """
    cfg = policy if policy is not None else load_scoring_config()

    l1_issues = score_l1(case, result, cfg)
    l2_issues = score_l2(case, result, cfg)

    l1 = LayerScore(layer="L1", status=layer_status_from_issues(l1_issues), issues=l1_issues)
    l2 = LayerScore(layer="L2", status=layer_status_from_issues(l2_issues), issues=l2_issues)

    from src.config.settings import get_settings

    settings = get_settings()

    if run_l3 is None:
        # Auto: run LLM trajectory judge whenever a key is available
        # JUDGE_ENABLED=false is the only hard opt-out (cost control).
        enable_l3 = settings.has_llm_key and settings.judge_enabled
    else:
        enable_l3 = bool(run_l3)

    l3_issues: list = []
    l3_summary: str | None = None
    l3_score: int | None = None
    l3_path_ok: bool | None = None
    l3_primary: str | None = None
    l3_issue_list: list[str] = []

    # Do not spend judge tokens when the agent itself failed on quota/key
    if enable_l3 and result.error_code in ("RATE_LIMIT", "MISSING_KEY", "API_ERROR"):
        enable_l3 = False
        l3_summary = (
            f"LLM trajectory judge skipped (agent error: {result.error_code})"
        )

    if enable_l3:
        from src.judge.trajectory_judge import run_trajectory_judge

        verdict = run_trajectory_judge(case, result, settings=settings)

        l3_summary = verdict.summary
        l3_score = verdict.score if not verdict.skipped else None
        l3_path_ok = verdict.path_ok if not verdict.skipped else None
        l3_primary = verdict.primary_failure if not verdict.skipped else None
        l3_issue_list = list(verdict.issues)

        if verdict.skipped:
            l3 = LayerScore(layer="L3", status="SKIP", issues=[])
            l3_summary = verdict.summary
        else:
            l3_issues = verdict.to_score_issues()
            if l3_issues:
                l3 = LayerScore(
                    layer="L3",
                    status=layer_status_from_issues(l3_issues),
                    issues=l3_issues,
                )
            else:
                l3 = LayerScore(layer="L3", status="PASS", issues=[])
                if not l3_summary:
                    l3_summary = f"LLM trajectory judge: path OK (score {verdict.score}/5)"
    else:
        l3 = LayerScore(layer="L3", status="SKIP", issues=[])
        if not settings.has_llm_key:
            l3_summary = "LLM trajectory judge skipped (no API key)"
        elif not settings.judge_enabled:
            l3_summary = "LLM trajectory judge disabled (JUDGE_ENABLED=false)"
        else:
            l3_summary = "LLM trajectory judge skipped"

    all_issues = list(l1_issues) + list(l2_issues) + list(l3_issues)
    statuses = [l1.status, l2.status]
    if l3.status != "SKIP":
        statuses.append(l3.status)
    verdict_agg = merge_verdict(*statuses)
    reasons = [f"[{i.layer}/{i.severity}] {i.code}: {i.message}" for i in all_issues]

    score = ScoreResult(
        verdict=verdict_agg,
        l1=l1,
        l2=l2,
        l3=l3,
        issues=all_issues,
        reasons=reasons,
        case_id=result.case_id or case.get("id"),
        l3_summary=l3_summary,
        l3_score=l3_score,
        l3_path_ok=l3_path_ok,
        l3_primary_failure=l3_primary,
        l3_issues=l3_issue_list,
    )
    tax = classify_failure(score, result=result, case=case)
    score.taxonomy_label = tax.label
    score.taxonomy_rationale = tax.rationale
    score.taxonomy_secondary = list(tax.secondary)
    return score
