"""LLM trajectory judge — evaluates the agent's tool path (not only final prose)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from src.agent.types import AgentResult
from src.config.settings import Settings, get_settings
from src.llm.client import (
    LLMClientError,
    MissingAPIKeyError,
    OpenAICompatibleClient,
    RateLimitClientError,
)
from src.meter.free_tier import get_meter
from src.scoring.models import ScoreIssue

TRAJECTORY_JUDGE_SYSTEM = """You are an AI Test Engineer scoring a TOOL-CALLING AGENT TRAJECTORY.

Focus on the PATH the agent took: which tools, order, arguments, and whether the
final answer honestly reflects tool results. Do NOT only judge writing style.

Evaluate against the user request AND any expected constraints provided.

Checklist:
1. Required tools for the request (or expected.must_call_tools) were called.
2. Forbidden tools (or expected.must_not_call_tools) were NOT called.
3. Dependent tools are ordered correctly (e.g. create_bug before assign_owner).
4. Arguments are sensible for the request (severity, team, non-empty title).
5. Final answer does not invent bug IDs or claim actions that never happened.
6. No hallucinated/unregistered tools.

Return ONLY valid JSON (no markdown fences):
{
  "pass": true/false,
  "score": 1-5,
  "path_ok": true/false,
  "primary_failure": "OK|MISSING_TOOL|WRONG_TOOL|ORDER_ERROR|BAD_ARGS|ANSWER_LIE|HALLUCINATED_TOOL|OTHER",
  "issues": ["short bullet findings"],
  "summary": "one sentence on trajectory quality"
}

Rules:
- score 5 = correct path + honest answer
- score 3 = minor extra tools or soft issues but intent met
- score 1 = wrong/missing path or answer lies about tools
- pass=true only if path_ok=true AND score >= 3
"""


@dataclass
class TrajectoryJudgeVerdict:
    """Structured LLM verdict on an agent trajectory."""

    passed: bool
    score: int
    path_ok: bool
    summary: str
    primary_failure: str
    issues: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_score_issues(self) -> list[ScoreIssue]:
        if self.skipped:
            return []
        if self.passed:
            return []
        detail_bits = list(self.issues) or [self.summary]
        return [
            ScoreIssue(
                layer="L3",
                code="TRAJECTORY_JUDGE_FAIL",
                message=(
                    f"LLM trajectory judge score={self.score}/5 "
                    f"path_ok={self.path_ok} [{self.primary_failure}]: "
                    f"{self.summary}"
                ),
                severity="critical",
                details={
                    "score": self.score,
                    "path_ok": self.path_ok,
                    "primary_failure": self.primary_failure,
                    "issues": self.issues,
                    "summary": self.summary,
                },
            )
        ]


def _trajectory_payload(result: AgentResult) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for s in result.trajectory:
        if s.kind == "tool":
            steps.append(
                {
                    "step": s.step,
                    "tool": s.tool,
                    "args": s.args or {},
                    "result_ok": (s.result or {}).get("ok"),
                    "result_data": (s.result or {}).get("data"),
                    "result_error": (s.result or {}).get("error"),
                }
            )
        else:
            steps.append(
                {
                    "step": s.step,
                    "kind": "final",
                    "content": s.content or result.final_answer,
                }
            )
    return steps


def run_trajectory_judge(
    case: dict[str, Any],
    result: AgentResult,
    *,
    client: OpenAICompatibleClient | None = None,
    settings: Settings | None = None,
    threshold: int = 3,
) -> TrajectoryJudgeVerdict:
    """
    Ask an LLM to score the tool-calling trajectory.

    Requires API key. On missing key / errors → skipped verdict (not a hard suite crash).
    """
    settings = settings or get_settings()
    if not settings.has_llm_key and client is None:
        return TrajectoryJudgeVerdict(
            passed=True,
            score=0,
            path_ok=False,
            summary="LLM trajectory judge skipped (no API key)",
            primary_failure="OTHER",
            skipped=True,
            skip_reason="MISSING_KEY",
        )

    client = client or OpenAICompatibleClient(settings)
    expected = case.get("expected") or {}
    user_payload = {
        "case_id": case.get("id"),
        "user_request": result.input,
        "expected_constraints": {
            "must_call_tools": expected.get("must_call_tools"),
            "must_not_call_tools": expected.get("must_not_call_tools"),
            "optional_tools": expected.get("optional_tools"),
            "order_constraints": expected.get("order_constraints"),
            "create_bug": expected.get("create_bug"),
            "assign_owner": expected.get("assign_owner"),
        },
        "actual_tool_names": result.tool_names,
        "trajectory": _trajectory_payload(result),
        "final_answer": result.final_answer,
        "mode": result.mode,
    }
    user_msg = (
        "Evaluate this agent trajectory as JSON only.\n\n"
        + json.dumps(user_payload, ensure_ascii=False, indent=2)
    )

    try:
        resp = client.chat(
            [
                {"role": "system", "content": TRAJECTORY_JUDGE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            tools=None,
            temperature=0,
        )
        get_meter().record_judge(resp.usage)
        payload = _parse_judge_json(resp.content or "")
    except MissingAPIKeyError:
        return TrajectoryJudgeVerdict(
            passed=True,
            score=0,
            path_ok=False,
            summary="LLM trajectory judge skipped (no API key)",
            primary_failure="OTHER",
            skipped=True,
            skip_reason="MISSING_KEY",
        )
    except (RateLimitClientError, LLMClientError) as exc:
        return TrajectoryJudgeVerdict(
            passed=True,
            score=0,
            path_ok=False,
            summary=f"LLM trajectory judge error: {exc}",
            primary_failure="OTHER",
            skipped=True,
            skip_reason=getattr(exc, "error_code", "API_ERROR") or "API_ERROR",
            raw={"error": str(exc)},
        )

    if not payload:
        return TrajectoryJudgeVerdict(
            passed=False,
            score=1,
            path_ok=False,
            summary="LLM trajectory judge returned unparseable output",
            primary_failure="OTHER",
            issues=["UNPARSEABLE_JUDGE_OUTPUT"],
            raw={"raw_text": (resp.content or "")[:500]},
        )

    score = int(payload.get("score") or 0)
    path_ok = bool(payload.get("path_ok", score >= threshold))
    passed = bool(payload.get("pass")) if "pass" in payload else (
        path_ok and score >= threshold
    )
    # Enforce consistency with threshold
    if score < threshold or not path_ok:
        passed = False

    issues = payload.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]
    issues = [str(i) for i in issues]

    primary = str(payload.get("primary_failure") or ("OK" if passed else "OTHER"))
    summary = str(payload.get("summary") or "").strip() or (
        "Trajectory acceptable" if passed else "Trajectory failed LLM path review"
    )

    return TrajectoryJudgeVerdict(
        passed=passed,
        score=score,
        path_ok=path_ok,
        summary=summary,
        primary_failure=primary,
        issues=issues,
        skipped=False,
        raw=payload,
    )


def _parse_judge_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    # strip markdown fences if model ignores instructions
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.I)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return {}
    return {}
