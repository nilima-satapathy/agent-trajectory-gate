"""Offline FixtureSUT — deterministic trajectories without network or API keys."""

from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

from src.agent.types import AgentResult, TrajectoryStep
from src.tools.registry import ToolRegistry
from src.tools.store import TicketStore

# Placeholder resolved after create_bug when replaying fixtures
BUG_ID_PLACEHOLDERS = frozenset(
    {
        "$bug_id",
        "$last_bug_id",
        "{{bug_id}}",
        "{{last_bug_id}}",
    }
)


class FixtureSUTError(ValueError):
    """Invalid case / fixture payload."""


class FixtureSUT:
    """
    Case-bound offline agent SUT.

    Case shape (minimal):
      {
        "id": "triage-001",
        "input": "...",
        "fixture": {
          "final_answer": "...",
          "trajectory": [
            {"tool": "create_bug", "args": {...}},
            {"tool": "assign_owner", "args": {"bug_id": "$last_bug_id", "team": "web"}}
          ],
          "replay": true   # default true — execute tools against ToolRegistry
        }
      }

    Deliberate FAIL fixtures omit required tools or use bad args while still
    returning a final_answer so scorers can classify MISSING_TOOL / ANSWER_LIE later.
    """

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or ToolRegistry(TicketStore())

    def run(self, case: dict[str, Any]) -> AgentResult:
        """Run one golden/fixture case offline. No LLM imports or network."""
        t0 = time.perf_counter()
        if not isinstance(case, dict):
            raise FixtureSUTError("case must be a dict")

        case_id = case.get("id")
        user_input = str(case.get("input") or case.get("question") or "")
        fixture = case.get("fixture")
        if fixture is None:
            raise FixtureSUTError(
                f"case {case_id!r} missing 'fixture' block for FixtureSUT"
            )
        if not isinstance(fixture, dict):
            raise FixtureSUTError(f"case {case_id!r}: fixture must be an object")

        final_answer = fixture.get("final_answer")
        if final_answer is None:
            final_answer = fixture.get("answer")
        if final_answer is None:
            raise FixtureSUTError(
                f"case {case_id!r}: fixture.final_answer is required"
            )
        final_answer = str(final_answer)

        raw_steps = fixture.get("trajectory") or fixture.get("steps") or []

        if not isinstance(raw_steps, list):
            raise FixtureSUTError(
                f"case {case_id!r}: fixture.trajectory must be a list"
            )

        replay = fixture.get("replay", True)
        if not isinstance(replay, bool):
            replay = bool(replay)

        # Fresh store per run when replaying so cases stay independent
        if replay:
            self.registry.reset()

        trajectory: list[TrajectoryStep] = []
        last_bug_id: str | None = None
        step_i = 0

        for raw in raw_steps:
            if not isinstance(raw, dict):
                raise FixtureSUTError(
                    f"case {case_id!r}: trajectory step must be an object"
                )
            kind = str(raw.get("kind") or "tool").lower()
            step_i += 1

            if kind == "final":
                content = str(raw.get("content") or raw.get("final_answer") or "")
                trajectory.append(
                    TrajectoryStep(
                        step=step_i,
                        kind="final",
                        content=content,
                    )
                )
                continue

            tool = raw.get("tool") or raw.get("name")
            if not tool:
                raise FixtureSUTError(
                    f"case {case_id!r}: tool step missing 'tool' name"
                )
            tool = str(tool)
            args = raw.get("args") or raw.get("arguments") or {}
            if not isinstance(args, dict):
                raise FixtureSUTError(
                    f"case {case_id!r}: tool args must be an object"
                )
            args = deepcopy(args)
            args = self._resolve_placeholders(args, last_bug_id=last_bug_id)

            if replay:
                tool_result = self.registry.execute(tool, args)
                result_dict = tool_result.to_dict()
                if (
                    tool_result.ok
                    and tool == "create_bug"
                    and tool_result.data
                    and tool_result.data.get("bug_id")
                ):
                    last_bug_id = str(tool_result.data["bug_id"])
            else:
                # Use pre-authored result if present; else minimal stub
                if "result" in raw and isinstance(raw["result"], dict):
                    result_dict = deepcopy(raw["result"])
                else:
                    result_dict = {
                        "ok": True,
                        "tool": tool,
                        "data": raw.get("data"),
                    }
                # Track bug_id from static results for later placeholders
                data = result_dict.get("data") if isinstance(result_dict, dict) else None
                if isinstance(data, dict) and data.get("bug_id"):
                    last_bug_id = str(data["bug_id"])

            trajectory.append(
                TrajectoryStep(
                    step=step_i,
                    kind="tool",
                    tool=tool,
                    args=args,
                    result=result_dict,
                )
            )

        # Optional: inject real bug id(s) into final answer templates
        created_ids = [
            str((s.result or {}).get("data", {}).get("bug_id"))
            for s in trajectory
            if s.kind == "tool"
            and s.tool == "create_bug"
            and s.result
            and s.result.get("ok")
            and (s.result.get("data") or {}).get("bug_id")
        ]
        final_answer = self._resolve_answer_templates(
            final_answer,
            last_bug_id=last_bug_id,
            all_bug_ids=created_ids,
        )


        # Append final step for timeline UIs
        step_i += 1
        trajectory.append(
            TrajectoryStep(
                step=step_i,
                kind="final",
                content=final_answer,
            )
        )

        latency_ms = (time.perf_counter() - t0) * 1000.0
        snapshot = self.registry.snapshot() if replay else {}

        return AgentResult(
            input=user_input,
            final_answer=final_answer,
            trajectory=trajectory,
            mode="fixture",
            case_id=str(case_id) if case_id is not None else None,
            store_snapshot=snapshot,
            latency_ms=round(latency_ms, 3),
            model="fixture",
            meta={
                "replay": replay,
                "last_bug_id": last_bug_id,
            },
        )

    @staticmethod
    def _resolve_placeholders(
        args: dict[str, Any],
        *,
        last_bug_id: str | None,
    ) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for key, value in args.items():
            if isinstance(value, str) and value.strip() in BUG_ID_PLACEHOLDERS:
                if not last_bug_id:
                    raise FixtureSUTError(
                        f"Placeholder {value!r} used but no prior create_bug bug_id"
                    )
                resolved[key] = last_bug_id
            else:
                resolved[key] = value
        return resolved

    @staticmethod
    def _resolve_answer_templates(
        answer: str,
        *,
        last_bug_id: str | None,
        all_bug_ids: list[str] | None = None,
    ) -> str:
        out = answer
        ids = all_bug_ids or ([] if not last_bug_id else [last_bug_id])
        if ids:
            joined = ", ".join(ids)
            out = out.replace("{{bug_ids}}", joined)
            out = out.replace("$bug_ids", joined)
        if last_bug_id:
            for token in (
                "{{bug}}",
                "{{bug_id}}",
                "{{last_bug_id}}",
                "$last_bug_id",
                "$bug_id",
            ):
                out = out.replace(token, last_bug_id)
        return out




def run_fixture_case(
    case: dict[str, Any],
    registry: ToolRegistry | None = None,
) -> AgentResult:
    """Convenience: FixtureSUT().run(case)."""
    return FixtureSUT(registry=registry).run(case)
