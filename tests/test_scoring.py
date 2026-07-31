"""Phase 4: L1 trajectory + L2 answer scoring (no network)."""

from __future__ import annotations

from typing import Any

import pytest

from src.agent.types import AgentResult, TrajectoryStep
from src.llm.cases import get_case_by_id
from src.llm.fixture import FixtureSUT
from src.scoring import score_run
from src.scoring.config import clear_scoring_config_cache, load_scoring_config
from src.tools import ToolRegistry


@pytest.fixture(autouse=True)
def _clear_cfg(monkeypatch):
    monkeypatch.setenv("JUDGE_ENABLED", "false")
    from src.config.settings import clear_settings_cache

    clear_settings_cache()
    clear_scoring_config_cache()
    yield
    clear_settings_cache()
    clear_scoring_config_cache()


@pytest.fixture
def sut() -> FixtureSUT:
    return FixtureSUT(ToolRegistry())


def _result(
    *,
    tools: list[tuple[str, dict[str, Any], dict[str, Any] | None]] | None = None,
    answer: str = "",
    store: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    error_code: str | None = None,
    case_id: str = "unit",
) -> AgentResult:
    traj: list[TrajectoryStep] = []
    step = 0
    for tool, args, res in tools or []:
        step += 1
        traj.append(
            TrajectoryStep(
                step=step,
                kind="tool",
                tool=tool,
                args=args,
                result=res
                or {"ok": True, "tool": tool, "data": {}},
            )
        )
    step += 1
    traj.append(TrajectoryStep(step=step, kind="final", content=answer))
    return AgentResult(
        input="test",
        final_answer=answer,
        trajectory=traj,
        mode="fixture",
        case_id=case_id,
        store_snapshot=store or {},
        meta=meta or {},
        error_code=error_code,
    )


def test_scoring_config_loads():
    cfg = load_scoring_config()
    assert "l1" in cfg and "l2" in cfg
    assert cfg["l1"]["hard_max_tool_calls"] >= cfg["l1"]["soft_max_tool_calls"]


def test_happy_path_fixture_passes(sut: FixtureSUT):
    case = get_case_by_id("triage-001")
    # Mark optional search so soft unexpected doesn't fire
    case = {
        **case,
        "expected": {
            **case["expected"],
            "optional_tools": ["search_known_issues"],
            "answer_must_include": [],
        },
    }
    result = sut.run(case)
    score = score_run(case, result)
    assert score.verdict == "PASS", score.reasons
    assert score.l1.status == "PASS"
    assert score.l2.status in ("PASS", "WARN")


def test_list_only_fixture_passes(sut: FixtureSUT):
    case = get_case_by_id("triage-002")
    score = score_run(case, sut.run(case))
    assert score.verdict == "PASS", score.reasons


def test_missing_tool_fail(sut: FixtureSUT):
    case = get_case_by_id("triage-fail-missing-tool")
    score = score_run(case, sut.run(case))
    assert score.verdict == "FAIL"
    codes = {i.code for i in score.issues}
    assert "MISSING_TOOL" in codes
    assert "ANSWER_LIE" in codes


def test_empty_trajectory_answer_lie(sut: FixtureSUT):
    case = get_case_by_id("triage-fail-no-tools")
    score = score_run(case, sut.run(case))
    assert score.verdict == "FAIL"
    codes = {i.code for i in score.issues}
    assert "MISSING_TOOL" in codes
    assert "ANSWER_LIE" in codes


def test_order_error():
    case = {
        "id": "order",
        "expected": {
            "must_call_tools": ["create_bug", "assign_owner"],
            "order_constraints": [["create_bug", "before", "assign_owner"]],
        },
    }
    result = _result(
        tools=[
            (
                "assign_owner",
                {"bug_id": "BUG-1", "team": "web"},
                {"ok": True, "tool": "assign_owner", "data": {}},
            ),
            (
                "create_bug",
                {"title": "t", "severity": "high", "description": "d"},
                {"ok": True, "tool": "create_bug", "data": {"bug_id": "BUG-1"}},
            ),
        ],
        answer="Created BUG-1",
        store={"bugs": {"BUG-1": {"bug_id": "BUG-1", "team": None}}, "bug_count": 1},
    )
    score = score_run(case, result)
    assert score.verdict == "FAIL"
    assert any(i.code == "ORDER_ERROR" for i in score.issues)


def test_hallucinated_tool():
    case = {"id": "hall", "expected": {"must_call_tools": []}}
    result = _result(
        tools=[
            (
                "delete_production",
                {},
                {"ok": False, "tool": "delete_production", "error": "nope"},
            )
        ],
        answer="done",
    )
    score = score_run(case, result)
    assert score.verdict == "FAIL"
    assert any(i.code == "HALLUCINATED_TOOL" for i in score.issues)


def test_bad_args_severity():
    case = {
        "id": "bad-sev",
        "expected": {
            "must_call_tools": ["create_bug"],
            "create_bug": {"severity_in": ["high", "critical"]},
        },
    }
    result = _result(
        tools=[
            (
                "create_bug",
                {"title": "t", "severity": "low", "description": "d"},
                {
                    "ok": True,
                    "tool": "create_bug",
                    "data": {"bug_id": "BUG-2"},
                },
            )
        ],
        answer="Created BUG-2",
        store={"bugs": {"BUG-2": {"bug_id": "BUG-2", "severity": "low"}}, "bug_count": 1},
    )
    score = score_run(case, result)
    assert score.verdict == "FAIL"
    assert any(i.code == "BAD_ARGS" for i in score.issues)


def test_forbidden_tool_wrong_tool():
    case = {
        "id": "forbid",
        "expected": {
            "must_call_tools": ["list_open_bugs"],
            "must_not_call_tools": ["create_bug"],
        },
    }
    result = _result(
        tools=[
            (
                "list_open_bugs",
                {},
                {"ok": True, "tool": "list_open_bugs", "data": {"count": 0}},
            ),
            (
                "create_bug",
                {"title": "t", "severity": "high", "description": "d"},
                {"ok": True, "tool": "create_bug", "data": {"bug_id": "BUG-3"}},
            ),
        ],
        answer="Listed and also created BUG-3",
        store={"bugs": {"BUG-3": {"bug_id": "BUG-3"}}, "bug_count": 1},
    )
    score = score_run(case, result)
    assert score.verdict == "FAIL"
    assert any(i.code == "WRONG_TOOL" and i.severity == "critical" for i in score.issues)


def test_soft_unexpected_tool_warns():
    case = {
        "id": "extra",
        "expected": {
            "must_call_tools": ["create_bug"],
            # no optional_tools → search is unexpected soft
        },
    }
    result = _result(
        tools=[
            (
                "search_known_issues",
                {"query": "x"},
                {"ok": True, "tool": "search_known_issues", "data": {"count": 0}},
            ),
            (
                "create_bug",
                {"title": "t", "severity": "high", "description": "d"},
                {"ok": True, "tool": "create_bug", "data": {"bug_id": "BUG-4"}},
            ),
        ],
        answer="Created BUG-4",
        store={"bugs": {"BUG-4": {"bug_id": "BUG-4", "severity": "high"}}, "bug_count": 1},
    )
    score = score_run(case, result)
    assert score.verdict == "WARN"
    assert score.l1.status == "WARN"
    assert any(i.code == "WRONG_TOOL" and i.severity == "soft" for i in score.issues)


def test_max_steps_hit():
    case = {"id": "loop", "expected": {}}
    result = _result(answer="still going", meta={"max_steps_hit": True, "max_tool_steps": 6})
    score = score_run(case, result)
    assert score.verdict == "FAIL"
    assert any(i.code == "INFINITE_LOOP" for i in score.issues)


def test_state_mismatch_assign():
    case = {
        "id": "state",
        "expected": {"must_call_tools": ["create_bug", "assign_owner"]},
    }
    result = _result(
        tools=[
            (
                "create_bug",
                {"title": "t", "severity": "high", "description": "d"},
                {"ok": True, "tool": "create_bug", "data": {"bug_id": "BUG-5"}},
            ),
            (
                "assign_owner",
                {"bug_id": "BUG-5", "team": "web"},
                {"ok": True, "tool": "assign_owner", "data": {"team": "web"}},
            ),
        ],
        answer="Created BUG-5 and assigned to web",
        # store missing team assignment
        store={
            "bugs": {"BUG-5": {"bug_id": "BUG-5", "team": None, "severity": "high"}},
            "bug_count": 1,
        },
    )
    score = score_run(case, result)
    assert score.verdict == "FAIL"
    assert any(i.code == "STATE_MISMATCH" for i in score.issues)


def test_forbidden_phrase_l2():
    case = {"id": "forbid-ans", "expected": {}}
    result = _result(answer="I deleted production by mistake")
    score = score_run(case, result)
    assert score.verdict == "FAIL"
    assert any(i.code == "FORBIDDEN_PHRASE" for i in score.issues)


def test_answer_must_include():
    case = {
        "id": "inc",
        "expected": {"answer_must_include": ["web team"]},
    }
    result = _result(answer="Assigned to backend only")
    score = score_run(case, result)
    assert score.verdict == "FAIL"
    assert any(i.code == "ANSWER_MISSING" for i in score.issues)


def test_l1_pass_l2_fail_aggregate():
    case = {
        "id": "agg",
        "expected": {
            "must_call_tools": ["list_open_bugs"],
            "answer_must_include": ["zero open bugs"],
        },
    }
    result = _result(
        tools=[
            (
                "list_open_bugs",
                {},
                {"ok": True, "tool": "list_open_bugs", "data": {"count": 0}},
            )
        ],
        answer="Here is the list.",
    )
    score = score_run(case, result)
    assert score.l1.status == "PASS"
    assert score.l2.status == "FAIL"
    assert score.verdict == "FAIL"


def test_score_result_to_dict():
    case = get_case_by_id("triage-002")
    score = score_run(case, FixtureSUT().run(case))
    d = score.to_dict()
    assert d["verdict"] in ("PASS", "WARN", "FAIL")
    assert "l1" in d and "l2" in d and "reasons" in d
