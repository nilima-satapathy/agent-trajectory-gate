"""Shared agent run result shapes (fixture + live SUT)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TrajectoryStep:
    """One step in an agent trajectory (tool call or terminal)."""

    step: int
    kind: str  # "tool" | "final"
    tool: str | None = None
    args: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    content: str | None = None  # final text when kind == "final"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Drop null noise for cleaner reports
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class AgentResult:
    """
    Unified SUT output for scoring and the Trajectory Console.

    Live and fixture modes MUST return this shape so L1/L2 scorers are shared.
    """

    input: str
    final_answer: str
    trajectory: list[TrajectoryStep] = field(default_factory=list)
    mode: str = "fixture"  # fixture | live
    case_id: str | None = None
    store_snapshot: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    model: str | None = None
    error: str | None = None
    error_code: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def tool_names(self) -> list[str]:
        return [
            s.tool
            for s in self.trajectory
            if s.kind == "tool" and s.tool
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "input": self.input,
            "final_answer": self.final_answer,
            "trajectory": [s.to_dict() for s in self.trajectory],
            "mode": self.mode,
            "store_snapshot": self.store_snapshot,
            "latency_ms": self.latency_ms,
            "model": self.model,
            "error": self.error,
            "error_code": self.error_code,
            "meta": self.meta,
            "tool_names": self.tool_names,
        }
