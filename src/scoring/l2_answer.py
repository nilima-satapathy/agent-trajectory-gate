"""L2 final-answer consistency checks."""

from __future__ import annotations

import re
from typing import Any

from src.agent.types import AgentResult
from src.scoring.models import ScoreIssue

_BUG_ID_RE = re.compile(r"BUG-\d+", re.IGNORECASE)


def score_l2(
    case: dict[str, Any],
    result: AgentResult,
    policy: dict[str, Any],
) -> list[ScoreIssue]:
    issues: list[ScoreIssue] = []
    expected = case.get("expected") or {}
    if not isinstance(expected, dict):
        expected = {}

    l2 = policy.get("l2") or {}
    lie_cfg = policy.get("answer_lie") or {}
    answer = result.final_answer or ""
    answer_l = answer.lower()
    tool_names = set(result.tool_names)

    created_ids = _created_bug_ids(result)
    store_ids = set((result.store_snapshot or {}).get("bugs") or {})

    # --- must include ---
    must_include = list(expected.get("answer_must_include") or [])
    for token in must_include:
        token_s = str(token)
        # Special: $bug_id / {{bug_id}} means any created id must appear
        if token_s.strip() in ("$bug_id", "{{bug_id}}", "$last_bug_id", "{{last_bug_id}}"):
            if created_ids and not any(bid in answer for bid in created_ids):
                issues.append(
                    ScoreIssue(
                        layer="L2",
                        code="ANSWER_MISSING",
                        message="Answer must include created bug_id",
                        severity="critical",
                        details={"created_ids": created_ids},
                    )
                )
            continue
        if token_s.lower() not in answer_l and token_s not in answer:
            issues.append(
                ScoreIssue(
                    layer="L2",
                    code="ANSWER_MISSING",
                    message=f"Answer missing required phrase: {token_s!r}",
                    severity="critical",
                    details={"token": token_s},
                )
            )

    # --- forbidden phrases (global + case) ---
    forbidden = list(l2.get("forbidden_phrases") or [])
    forbidden.extend(expected.get("answer_must_not_include") or [])
    for phrase in forbidden:
        p = str(phrase).lower()
        if p and p in answer_l:
            issues.append(
                ScoreIssue(
                    layer="L2",
                    code="FORBIDDEN_PHRASE",
                    message=f"Answer contains forbidden phrase: {phrase!r}",
                    severity="critical",
                    details={"phrase": phrase},
                )
            )

    # --- answer lie: create claims without tool ---
    if l2.get("answer_lie_critical", True):
        create_subs = [str(s).lower() for s in (lie_cfg.get("create_claim_substrings") or [])]
        if "create_bug" not in tool_names:
            if any(s in answer_l for s in create_subs):
                issues.append(
                    ScoreIssue(
                        layer="L2",
                        code="ANSWER_LIE",
                        message="Answer claims bug creation but create_bug was not called",
                        severity="critical",
                        details={"tool_names": sorted(tool_names)},
                    )
                )
            # Invented BUG-#### not from tools/store
            mentioned = {m.upper() for m in _BUG_ID_RE.findall(answer)}
            known = {x.upper() for x in created_ids} | {x.upper() for x in store_ids}
            invented = sorted(mentioned - known)
            if invented:
                issues.append(
                    ScoreIssue(
                        layer="L2",
                        code="ANSWER_LIE",
                        message=f"Answer cites bug id(s) not created in trajectory: {', '.join(invented)}",
                        severity="critical",
                        details={"invented": invented, "known": sorted(known)},
                    )
                )

        assign_subs = [str(s).lower() for s in (lie_cfg.get("assign_claim_substrings") or [])]
        if "assign_owner" not in tool_names and any(s in answer_l for s in assign_subs):
            # Only flag if they also claim assignment meaningfully
            issues.append(
                ScoreIssue(
                    layer="L2",
                    code="ANSWER_LIE",
                    message="Answer claims assignment but assign_owner was not called",
                    severity="critical",
                    details={"tool_names": sorted(tool_names)},
                )
            )

    # --- soft: created bug id should appear in answer ---
    if (
        l2.get("require_bug_id_in_answer_when_created", True)
        and created_ids
        and not any(bid in answer for bid in created_ids)
    ):
        sev = "soft" if l2.get("require_bug_id_soft", True) else "critical"
        issues.append(
            ScoreIssue(
                layer="L2",
                code="ANSWER_MISSING",
                message="create_bug succeeded but answer does not mention bug_id",
                severity=sev,  # type: ignore[arg-type]
                details={"created_ids": created_ids},
            )
        )

    return issues


def _created_bug_ids(result: AgentResult) -> list[str]:
    ids: list[str] = []
    for s in result.trajectory:
        if s.kind != "tool" or s.tool != "create_bug":
            continue
        if not s.result or not s.result.get("ok"):
            continue
        data = s.result.get("data") or {}
        bid = data.get("bug_id")
        if bid:
            ids.append(str(bid))
    return ids
