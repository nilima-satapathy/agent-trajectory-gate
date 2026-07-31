"""Phase 3: FixtureSUT — offline trajectories, deliberate FAIL fixtures, no network."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.agent.types import AgentResult
from src.llm.cases import get_case_by_id, load_fixture_cases
from src.llm.fixture import FixtureSUT, FixtureSUTError, run_fixture_case
from src.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sut() -> FixtureSUT:
    return FixtureSUT(ToolRegistry())


def test_fixture_module_has_no_openai_import():
    """Guard: fixture path must not pull network LLM clients."""
    fixture_path = ROOT / "src" / "llm" / "fixture.py"
    tree = ast.parse(fixture_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "openai" not in alias.name.lower()
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "openai" not in node.module.lower()


def test_load_fixture_cases():
    cases = load_fixture_cases()
    assert len(cases) >= 4
    ids = {c["id"] for c in cases}
    assert "triage-001" in ids
    assert "triage-fail-missing-tool" in ids


def test_load_quick_tag_filter():
    quick = load_fixture_cases(tag="quick")
    assert len(quick) >= 3
    assert all("quick" in (c.get("tags") or []) for c in quick)


def test_run_happy_path_replays_tools(sut: FixtureSUT):
    case = get_case_by_id("triage-001")
    result = sut.run(case)

    assert isinstance(result, AgentResult)
    assert result.mode == "fixture"
    assert result.case_id == "triage-001"
    assert result.model == "fixture"
    assert result.error is None
    assert "create_bug" in result.tool_names
    assert "assign_owner" in result.tool_names
    # create before assign
    create_i = result.tool_names.index("create_bug")
    assign_i = result.tool_names.index("assign_owner")
    assert create_i < assign_i

    # Side effects real after replay
    assert result.store_snapshot["bug_count"] == 1
    bug_ids = list(result.store_snapshot["bugs"].keys())
    assert bug_ids[0].startswith("BUG-")
    assert result.store_snapshot["bugs"][bug_ids[0]]["team"] == "web"

    # Placeholder resolved in assign args
    assign_step = next(s for s in result.trajectory if s.tool == "assign_owner")
    assert assign_step.args is not None
    assert assign_step.args["bug_id"] == bug_ids[0]
    assert assign_step.result is not None
    assert assign_step.result["ok"] is True

    # Final step present
    assert result.trajectory[-1].kind == "final"
    assert result.final_answer
    assert bug_ids[0] in result.final_answer
    assert result.latency_ms >= 0



def test_run_list_only(sut: FixtureSUT):
    case = get_case_by_id("triage-002")
    result = sut.run(case)
    assert result.tool_names == ["list_open_bugs"]
    assert "create_bug" not in result.tool_names
    assert result.store_snapshot["bug_count"] == 0


def test_deliberate_fail_missing_tool(sut: FixtureSUT):
    """Fixture omits create/assign — usable later for MISSING_TOOL scoring demos."""
    case = get_case_by_id("triage-fail-missing-tool")
    result = sut.run(case)
    assert "create_bug" not in result.tool_names
    assert "assign_owner" not in result.tool_names
    assert result.tool_names == ["search_known_issues"]
    # Answer still claims success (answer lie material for phase 4)
    assert "BUG-9999" in result.final_answer
    expected = case["expected"]["must_call_tools"]
    assert "create_bug" in expected and "assign_owner" in expected
    # Required tools absent → scoring (phase 4) can mark MISSING_TOOL
    assert "create_bug" not in result.tool_names
    assert "assign_owner" not in result.tool_names



def test_deliberate_fail_empty_trajectory(sut: FixtureSUT):
    case = get_case_by_id("triage-fail-no-tools")
    result = sut.run(case)
    assert result.tool_names == []
    assert result.store_snapshot["bug_count"] == 0
    assert "BUG-4242" in result.final_answer
    assert result.trajectory[-1].kind == "final"


def test_result_to_dict_shape(sut: FixtureSUT):
    result = sut.run(get_case_by_id("triage-002"))
    d = result.to_dict()
    for key in (
        "case_id",
        "input",
        "final_answer",
        "trajectory",
        "mode",
        "store_snapshot",
        "latency_ms",
        "tool_names",
    ):
        assert key in d
    assert d["mode"] == "fixture"
    assert isinstance(d["trajectory"], list)


def test_missing_fixture_block_raises(sut: FixtureSUT):
    with pytest.raises(FixtureSUTError, match="fixture"):
        sut.run({"id": "x", "input": "hi"})


def test_placeholder_without_create_raises(sut: FixtureSUT):
    case = {
        "id": "bad-placeholder",
        "input": "assign something",
        "fixture": {
            "final_answer": "done",
            "trajectory": [
                {
                    "tool": "assign_owner",
                    "args": {"bug_id": "$last_bug_id", "team": "web"},
                }
            ],
        },
    }
    with pytest.raises(FixtureSUTError, match="Placeholder"):
        sut.run(case)


def test_replay_false_uses_static_result(sut: FixtureSUT):
    case = {
        "id": "static-1",
        "input": "static path",
        "fixture": {
            "replay": False,
            "final_answer": "ok",
            "trajectory": [
                {
                    "tool": "create_bug",
                    "args": {
                        "title": "T",
                        "severity": "low",
                        "description": "D",
                    },
                    "result": {
                        "ok": True,
                        "tool": "create_bug",
                        "data": {"bug_id": "BUG-STATIC"},
                    },
                }
            ],
        },
    }
    result = sut.run(case)
    assert result.tool_names == ["create_bug"]
    step = result.trajectory[0]
    assert step.result is not None
    assert step.result["data"]["bug_id"] == "BUG-STATIC"
    # No real store mutation when replay=False
    assert result.store_snapshot == {}


def test_run_fixture_case_helper():
    case = get_case_by_id("triage-002")
    result = run_fixture_case(case)
    assert result.case_id == "triage-002"


def test_cases_independent_resets_store(sut: FixtureSUT):
    sut.run(get_case_by_id("triage-001"))
    r2 = sut.run(get_case_by_id("triage-002"))
    # triage-002 should not keep triage-001 bugs after reset-on-replay
    assert r2.store_snapshot["bug_count"] == 0
