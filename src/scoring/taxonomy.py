"""Deterministic failure taxonomy from score issues + trajectory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agent.types import AgentResult
from src.scoring.models import ScoreIssue, ScoreResult, Verdict

# Higher priority = preferred as primary when multiple critical codes present
_PRIORITY: list[str] = [
    "RATE_LIMIT",
    "MODEL_ERROR",
    "HALLUCINATED_TOOL",
    "INFINITE_LOOP",
    "MISSING_TOOL",
    "ORDER_ERROR",
    "BAD_ARGS",
    "STATE_MISMATCH",
    "WRONG_TOOL",
    "ANSWER_LIE",
    "FORBIDDEN_PHRASE",
    "ANSWER_MISSING",
    "TRAJECTORY_JUDGE_FAIL",
]

TAXONOMY_LABELS = frozenset(
    {
        "OK",
        "WRONG_TOOL",
        "MISSING_TOOL",
        "BAD_ARGS",
        "ORDER_ERROR",
        "HALLUCINATED_TOOL",
        "INFINITE_LOOP",
        "STATE_MISMATCH",
        "ANSWER_LIE",
        "MODEL_ERROR",
        "RATE_LIMIT",
        # Soft / residual buckets used when only soft or uncategorized
        "ANSWER_QUALITY",
        "OTHER",
    }
)

# Map issue codes → taxonomy labels
_CODE_TO_LABEL: dict[str, str] = {
    "RATE_LIMIT": "RATE_LIMIT",
    "MODEL_ERROR": "MODEL_ERROR",
    "HALLUCINATED_TOOL": "HALLUCINATED_TOOL",
    "INFINITE_LOOP": "INFINITE_LOOP",
    "MISSING_TOOL": "MISSING_TOOL",
    "ORDER_ERROR": "ORDER_ERROR",
    "BAD_ARGS": "BAD_ARGS",
    "STATE_MISMATCH": "STATE_MISMATCH",
    "WRONG_TOOL": "WRONG_TOOL",
    "ANSWER_LIE": "ANSWER_LIE",
    "FORBIDDEN_PHRASE": "ANSWER_LIE",  # policy-ish lie / unsafe claim
    "ANSWER_MISSING": "ANSWER_QUALITY",
    "TRAJECTORY_JUDGE_FAIL": "OTHER",
}



@dataclass(frozen=True)
class TaxonomyResult:
    label: str
    rationale: str
    secondary: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "rationale": self.rationale,
            "secondary": list(self.secondary),
        }


def classify_failure(
    score: ScoreResult,
    result: AgentResult | None = None,
    case: dict[str, Any] | None = None,
) -> TaxonomyResult:
    """
    Pick a single primary taxonomy label.

    Priority: MODEL_ERROR > path integrity > answer lie > soft answer quality > OK.
    Soft-only WRONG_TOOL still maps to WRONG_TOOL (with soft rationale).
    """
    _ = result, case  # reserved for future trajectory-aware heuristics

    if score.verdict == "PASS" and not score.issues:
        return TaxonomyResult(
            label="OK",
            rationale="All L1/L2 checks passed",
            secondary=[],
        )

    # Prefer critical issues for primary; fall back to soft
    critical = [i for i in score.issues if i.severity == "critical"]
    soft = [i for i in score.issues if i.severity == "soft"]
    pool = critical if critical else soft

    if not pool:
        if score.verdict == "PASS":
            return TaxonomyResult(
                label="OK",
                rationale="Verdict PASS with no classified issues",
                secondary=[],
            )
        return TaxonomyResult(
            label="OTHER",
            rationale=f"Verdict {score.verdict} without issue codes",
            secondary=[],
        )

    primary_issue = _pick_primary(pool)
    label = _CODE_TO_LABEL.get(primary_issue.code, "OTHER")
    if label not in TAXONOMY_LABELS:
        label = "OTHER"

    secondary_codes = sorted(
        {
            _CODE_TO_LABEL.get(i.code, i.code)
            for i in score.issues
            if i is not primary_issue
        }
        - {label}
    )

    rationale = f"{primary_issue.code}: {primary_issue.message}"
    if primary_issue.severity == "soft" and score.verdict == "WARN":
        rationale = f"(soft) {rationale}"

    return TaxonomyResult(
        label=label,
        rationale=rationale,
        secondary=secondary_codes,
    )


def _pick_primary(issues: list[ScoreIssue]) -> ScoreIssue:
    def rank(issue: ScoreIssue) -> tuple[int, int]:
        try:
            p = _PRIORITY.index(issue.code)
        except ValueError:
            p = len(_PRIORITY)
        # critical already filtered; keep stable by code name
        return (p, 0)

    return sorted(issues, key=rank)[0]


def attach_taxonomy(score: ScoreResult, tax: TaxonomyResult) -> ScoreResult:
    """Return a new ScoreResult-like update via mutating optional fields on reasons.

    We store taxonomy on the ScoreResult by extending reasons header and
    returning the same object after setting attributes dynamically for report use.
    """
    # Attach as explicit attributes for report/console consumers
    score.taxonomy_label = tax.label  # type: ignore[attr-defined]
    score.taxonomy_rationale = tax.rationale  # type: ignore[attr-defined]
    score.taxonomy_secondary = list(tax.secondary)  # type: ignore[attr-defined]
    return score


def taxonomy_counts(labels: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
