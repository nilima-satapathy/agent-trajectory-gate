"""Scoring result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["critical", "soft"]
LayerStatus = Literal["PASS", "WARN", "FAIL", "SKIP"]
Verdict = Literal["PASS", "WARN", "FAIL"]


@dataclass
class ScoreIssue:
    layer: str  # L1 | L2 | L3
    code: str  # MISSING_TOOL, BAD_ARGS, ANSWER_LIE, ...
    message: str
    severity: Severity = "critical"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LayerScore:
    layer: str
    status: LayerStatus
    issues: list[ScoreIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "status": self.status,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class ScoreResult:
    verdict: Verdict
    l1: LayerScore
    l2: LayerScore
    l3: LayerScore | None = None
    issues: list[ScoreIssue] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    case_id: str | None = None
    taxonomy_label: str | None = None
    taxonomy_rationale: str | None = None
    taxonomy_secondary: list[str] = field(default_factory=list)
    # LLM trajectory judge (L3) extras for UI / reports
    l3_summary: str | None = None
    l3_score: int | None = None
    l3_path_ok: bool | None = None
    l3_primary_failure: str | None = None
    l3_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "case_id": self.case_id,
            "taxonomy": {
                "label": self.taxonomy_label,
                "rationale": self.taxonomy_rationale,
                "secondary": list(self.taxonomy_secondary),
            },
            "l1": self.l1.to_dict(),
            "l2": self.l2.to_dict(),
            "l3": self.l3.to_dict() if self.l3 else {"layer": "L3", "status": "SKIP", "issues": []},
            "llm_trajectory_judge": {
                "summary": self.l3_summary,
                "score": self.l3_score,
                "path_ok": self.l3_path_ok,
                "primary_failure": self.l3_primary_failure,
                "issues": list(self.l3_issues),
            },
            "issues": [i.to_dict() for i in self.issues],
            "reasons": self.reasons,
        }




def layer_status_from_issues(issues: list[ScoreIssue]) -> LayerStatus:
    if any(i.severity == "critical" for i in issues):
        return "FAIL"
    if any(i.severity == "soft" for i in issues):
        return "WARN"
    return "PASS"


def merge_verdict(*statuses: LayerStatus) -> Verdict:
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    if any(s == "WARN" for s in statuses):
        return "WARN"
    return "PASS"
