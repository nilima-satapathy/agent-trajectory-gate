"""L1 deterministic trajectory / path gates."""

from __future__ import annotations

from typing import Any

from src.agent.types import AgentResult, TrajectoryStep
from src.scoring.models import ScoreIssue
from src.tools.registry import MVP_TOOL_NAMES


def _tool_steps(result: AgentResult) -> list[TrajectoryStep]:
    return [s for s in result.trajectory if s.kind == "tool" and s.tool]


def _tool_names(result: AgentResult) -> list[str]:
    return [s.tool for s in _tool_steps(result) if s.tool]


def _first_index(names: list[str], tool: str) -> int | None:
    try:
        return names.index(tool)
    except ValueError:
        return None


def score_l1(
    case: dict[str, Any],
    result: AgentResult,
    policy: dict[str, Any],
) -> list[ScoreIssue]:
    """Return L1 issues (critical and soft)."""
    issues: list[ScoreIssue] = []
    expected = case.get("expected") or {}
    if not isinstance(expected, dict):
        expected = {}

    l1 = policy.get("l1") or {}
    names = _tool_names(result)
    steps = _tool_steps(result)
    registered = set(MVP_TOOL_NAMES)

    # --- Provider / model errors from live agent ---
    if result.error_code == "RATE_LIMIT":
        issues.append(
            ScoreIssue(
                layer="L1",
                code="RATE_LIMIT",
                message=result.error
                or "Provider rate limit (429). Wait or switch to a lighter model.",
                severity="critical",
                details={"error_code": result.error_code},
            )
        )
    elif result.error_code == "MISSING_KEY":
        issues.append(
            ScoreIssue(
                layer="L1",
                code="MODEL_ERROR",
                message=result.error or "API key missing for live agent",
                severity="critical",
                details={"error_code": result.error_code},
            )
        )
    elif result.error_code in ("MODEL_ERROR", "API_ERROR"):
        issues.append(
            ScoreIssue(
                layer="L1",
                code="MODEL_ERROR",
                message=result.error or "Model/API error during agent run",
                severity="critical",
                details={"error_code": result.error_code},
            )
        )


    meta = result.meta or {}
    if l1.get("max_steps_critical", True) and (
        meta.get("max_steps_hit") or result.error_code == "MAX_STEPS"
    ):
        issues.append(
            ScoreIssue(
                layer="L1",
                code="INFINITE_LOOP",
                message="Agent hit max tool steps without a clean completion",
                severity="critical",
                details={"max_tool_steps": meta.get("max_tool_steps")},
            )
        )

    # --- Required tools ---
    must = list(expected.get("must_call_tools") or [])
    missing = [t for t in must if t not in names]
    if missing:
        issues.append(
            ScoreIssue(
                layer="L1",
                code="MISSING_TOOL",
                message=f"Required tool(s) not called: {', '.join(missing)}",
                severity="critical",
                details={"missing": missing, "called": names},
            )
        )

    # --- Forbidden tools ---
    must_not = list(expected.get("must_not_call_tools") or [])
    forbidden_hits = [t for t in must_not if t in names]
    if forbidden_hits:
        sev = "critical" if l1.get("forbidden_tools_critical", True) else "soft"
        issues.append(
            ScoreIssue(
                layer="L1",
                code="WRONG_TOOL",
                message=f"Forbidden tool(s) were called: {', '.join(forbidden_hits)}",
                severity=sev,  # type: ignore[arg-type]
                details={"forbidden_hits": forbidden_hits},
            )
        )

    # --- Order constraints: [tool_a, "before", tool_b] ---
    for constraint in expected.get("order_constraints") or []:
        if not isinstance(constraint, (list, tuple)) or len(constraint) != 3:
            continue
        a, rel, b = constraint[0], str(constraint[1]).lower(), constraint[2]
        if rel != "before":
            continue
        ia, ib = _first_index(names, str(a)), _first_index(names, str(b))
        if ia is None or ib is None:
            # Missing handled by MISSING_TOOL; skip order if either absent
            continue
        if ia >= ib:
            issues.append(
                ScoreIssue(
                    layer="L1",
                    code="ORDER_ERROR",
                    message=f"Order violation: {a} must appear before {b}",
                    severity="critical",
                    details={"constraint": list(constraint), "order": names},
                )
            )

    # --- Hallucinated / unregistered tools ---
    for tool in names:
        if tool not in registered:
            issues.append(
                ScoreIssue(
                    layer="L1",
                    code="HALLUCINATED_TOOL",
                    message=f"Unregistered tool called: {tool}",
                    severity="critical",
                    details={"tool": tool},
                )
            )

    # --- Arg constraints ---
    issues.extend(_check_arg_constraints(expected, steps))

    # --- Step budget ---
    soft_max = int(l1.get("soft_max_tool_calls", 8))
    hard_max = int(l1.get("hard_max_tool_calls", 12))
    n = len(names)
    if n > hard_max:
        issues.append(
            ScoreIssue(
                layer="L1",
                code="INFINITE_LOOP",
                message=f"Too many tool calls: {n} > hard max {hard_max}",
                severity="critical",
                details={"count": n, "hard_max": hard_max},
            )
        )
    elif n > soft_max:
        issues.append(
            ScoreIssue(
                layer="L1",
                code="INFINITE_LOOP",
                message=f"Tool call count high: {n} > soft max {soft_max}",
                severity="soft",
                details={"count": n, "soft_max": soft_max},
            )
        )

    # --- Unexpected tools (soft) ---
    if l1.get("unexpected_tools_soft", True) and must:
        optional = set(expected.get("optional_tools") or [])
        allowed = set(must) | optional | set(must_not)
        # must_not are not "allowed" to call; unexpected = called - must - optional
        unexpected = [t for t in names if t not in set(must) | optional]
        # Don't double-count forbidden tools already flagged
        unexpected = [t for t in unexpected if t not in must_not]
        # Allow search as common optional unless list-only forbids everything else
        if unexpected:
            issues.append(
                ScoreIssue(
                    layer="L1",
                    code="WRONG_TOOL",
                    message=f"Unexpected extra tool(s): {', '.join(sorted(set(unexpected)))}",
                    severity="soft",
                    details={"unexpected": sorted(set(unexpected)), "allowed_hint": sorted(allowed)},
                )
            )

    # --- State checks against store snapshot ---
    issues.extend(_check_state(expected, result, steps))

    return issues


def _check_arg_constraints(
    expected: dict[str, Any],
    steps: list[TrajectoryStep],
) -> list[ScoreIssue]:
    issues: list[ScoreIssue] = []

    create_exp = expected.get("create_bug") or {}
    if isinstance(create_exp, dict) and create_exp:
        create_steps = [s for s in steps if s.tool == "create_bug"]
        for s in create_steps:
            args = s.args or {}
            sev = str(args.get("severity", "")).strip().lower()
            allowed = create_exp.get("severity_in")
            if allowed and sev not in [str(x).lower() for x in allowed]:
                issues.append(
                    ScoreIssue(
                        layer="L1",
                        code="BAD_ARGS",
                        message=f"create_bug severity {sev!r} not in {allowed}",
                        severity="critical",
                        details={"args": args, "severity_in": allowed},
                    )
                )
            if create_exp.get("require_title", True):
                title = str(args.get("title") or "").strip()
                if not title:
                    issues.append(
                        ScoreIssue(
                            layer="L1",
                            code="BAD_ARGS",
                            message="create_bug missing non-empty title",
                            severity="critical",
                            details={"args": args},
                        )
                    )
            # Tool-level validation failure on execute
            if s.result and s.result.get("ok") is False:
                issues.append(
                    ScoreIssue(
                        layer="L1",
                        code="BAD_ARGS",
                        message=f"create_bug execution failed: {s.result.get('error')}",
                        severity="critical",
                        details={"result": s.result},
                    )
                )

    assign_exp = expected.get("assign_owner") or {}
    if isinstance(assign_exp, dict):
        for s in steps:
            if s.tool != "assign_owner":
                continue
            args = s.args or {}
            team_in = assign_exp.get("team_in")
            team = str(args.get("team") or "").strip().lower()
            if team_in and team not in [str(x).lower() for x in team_in]:
                issues.append(
                    ScoreIssue(
                        layer="L1",
                        code="BAD_ARGS",
                        message=f"assign_owner team {team!r} not in {team_in}",
                        severity="critical",
                        details={"args": args},
                    )
                )
            if s.result and s.result.get("ok") is False:
                issues.append(
                    ScoreIssue(
                        layer="L1",
                        code="BAD_ARGS",
                        message=f"assign_owner failed: {s.result.get('error')}",
                        severity="critical",
                        details={"result": s.result},
                    )
                )

    return issues


def _check_state(
    expected: dict[str, Any],
    result: AgentResult,
    steps: list[TrajectoryStep],
) -> list[ScoreIssue]:
    issues: list[ScoreIssue] = []
    snap = result.store_snapshot or {}
    bugs = snap.get("bugs") or {}

    created_ids: list[str] = []
    for s in steps:
        if s.tool == "create_bug" and s.result and s.result.get("ok"):
            data = s.result.get("data") or {}
            bid = data.get("bug_id")
            if bid:
                created_ids.append(str(bid))

    for bid in created_ids:
        if bid not in bugs:
            issues.append(
                ScoreIssue(
                    layer="L1",
                    code="STATE_MISMATCH",
                    message=f"create_bug returned {bid} but store has no such bug",
                    severity="critical",
                    details={"bug_id": bid},
                )
            )

    for s in steps:
        if s.tool != "assign_owner":
            continue
        if not (s.result and s.result.get("ok")):
            continue
        args = s.args or {}
        bid = str(args.get("bug_id") or "")
        team = str(args.get("team") or "").lower()
        bug = bugs.get(bid)
        if not bug:
            issues.append(
                ScoreIssue(
                    layer="L1",
                    code="STATE_MISMATCH",
                    message=f"assign_owner ok for {bid} but bug missing from store",
                    severity="critical",
                    details={"bug_id": bid},
                )
            )
        elif team and str(bug.get("team") or "").lower() != team:
            issues.append(
                ScoreIssue(
                    layer="L1",
                    code="STATE_MISMATCH",
                    message=f"Store team for {bid} is {bug.get('team')!r}, expected {team!r}",
                    severity="critical",
                    details={"bug": bug, "expected_team": team},
                )
            )

    # Optional explicit expected state
    exp_state = expected.get("store") or {}
    if isinstance(exp_state, dict):
        if "min_bugs" in exp_state:
            min_bugs = int(exp_state["min_bugs"])
            if int(snap.get("bug_count") or 0) < min_bugs:
                issues.append(
                    ScoreIssue(
                        layer="L1",
                        code="STATE_MISMATCH",
                        message=f"Expected at least {min_bugs} bugs in store",
                        severity="critical",
                        details={"bug_count": snap.get("bug_count")},
                    )
                )

    return issues
