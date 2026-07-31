"""Phase 2: tool registry — schemas, execute, side effects (no network)."""

from __future__ import annotations

import pytest

from src.tools import (
    ALLOWED_SEVERITIES,
    MVP_TOOL_NAMES,
    TicketStore,
    ToolRegistry,
)


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry(TicketStore())


def test_mvp_tool_names_present(registry: ToolRegistry):
    names = set(registry.names())
    for required in (
        "search_known_issues",
        "create_bug",
        "assign_owner",
        "lookup_user",
        "list_open_bugs",
    ):
        assert required in names
    assert tuple(registry.names()) == MVP_TOOL_NAMES


def test_tool_schemas_openai_compatible(registry: ToolRegistry):
    schemas = registry.tool_schemas()
    assert len(schemas) == len(MVP_TOOL_NAMES)
    names = set()
    for item in schemas:
        assert item["type"] == "function"
        fn = item["function"]
        assert "name" in fn and "description" in fn and "parameters" in fn
        params = fn["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        names.add(fn["name"])
    assert names == set(MVP_TOOL_NAMES)


def test_create_bug_side_effect(registry: ToolRegistry):
    result = registry.execute(
        "create_bug",
        {
            "title": "Login fails on Chrome",
            "severity": "high",
            "description": "Repro after last deploy",
        },
    )
    assert result.ok is True
    assert result.error is None
    assert result.data is not None
    bug_id = result.data["bug_id"]
    assert bug_id.startswith("BUG-")
    snap = registry.snapshot()
    assert snap["bug_count"] == 1
    assert bug_id in snap["bugs"]
    assert snap["bugs"][bug_id]["severity"] == "high"
    assert snap["bugs"][bug_id]["title"] == "Login fails on Chrome"


def test_create_then_assign_owner(registry: ToolRegistry):
    created = registry.execute(
        "create_bug",
        {
            "title": "Checkout 500",
            "severity": "critical",
            "description": "Null ref on place order",
        },
    )
    assert created.ok
    bug_id = created.data["bug_id"]

    assigned = registry.execute(
        "assign_owner",
        {"bug_id": bug_id, "team": "web"},
    )
    assert assigned.ok is True
    assert assigned.data["team"] == "web"
    assert assigned.data["bug"]["team"] == "web"

    snap = registry.snapshot()
    assert snap["bugs"][bug_id]["team"] == "web"


def test_assign_unknown_bug_id(registry: ToolRegistry):
    result = registry.execute(
        "assign_owner",
        {"bug_id": "BUG-9999", "team": "web"},
    )
    assert result.ok is False
    assert result.error_code == "VALIDATION_ERROR"
    assert "Unknown bug_id" in (result.error or "")


def test_unknown_tool_rejected_no_side_effect(registry: ToolRegistry):
    before = registry.snapshot()["bug_count"]
    result = registry.execute("delete_production", {"confirm": True})
    assert result.ok is False
    assert result.error_code == "UNKNOWN_TOOL"
    assert "Unknown tool" in (result.error or "")
    assert registry.has_tool("delete_production") is False
    assert registry.snapshot()["bug_count"] == before


def test_create_bug_invalid_severity(registry: ToolRegistry):
    result = registry.execute(
        "create_bug",
        {
            "title": "x",
            "severity": "super-urgent",
            "description": "y",
        },
    )
    assert result.ok is False
    assert result.error_code == "VALIDATION_ERROR"
    assert registry.snapshot()["bug_count"] == 0


def test_create_bug_missing_required_arg(registry: ToolRegistry):
    result = registry.execute(
        "create_bug",
        {"title": "Only title", "severity": "low"},
    )
    assert result.ok is False
    assert result.error_code == "VALIDATION_ERROR"
    assert "description" in (result.error or "").lower()


def test_search_known_issues(registry: ToolRegistry):
    result = registry.execute(
        "search_known_issues",
        {"query": "chrome login deploy"},
    )
    assert result.ok is True
    assert result.data["count"] >= 1
    titles = " ".join(i["title"].lower() for i in result.data["issues"])
    assert "chrome" in titles or "login" in titles


def test_lookup_user_found_and_missing(registry: ToolRegistry):
    found = registry.execute("lookup_user", {"email": "alice@example.com"})
    assert found.ok is True
    assert found.data["found"] is True
    assert found.data["user"]["team"] == "web"

    missing = registry.execute("lookup_user", {"email": "nobody@example.com"})
    assert missing.ok is True
    assert missing.data["found"] is False


def test_list_open_bugs_filter(registry: ToolRegistry):
    registry.execute(
        "create_bug",
        {"title": "A", "severity": "high", "description": "d1"},
    )
    registry.execute(
        "create_bug",
        {"title": "B", "severity": "low", "description": "d2"},
    )
    all_bugs = registry.execute("list_open_bugs", {})
    assert all_bugs.ok and all_bugs.data["count"] == 2

    high_only = registry.execute("list_open_bugs", {"severity": "high"})
    assert high_only.ok and high_only.data["count"] == 1
    assert high_only.data["bugs"][0]["severity"] == "high"


def test_severity_normalized_case(registry: ToolRegistry):
    result = registry.execute(
        "create_bug",
        {"title": "T", "severity": "HIGH", "description": "D"},
    )
    assert result.ok
    assert result.data["bug"]["severity"] == "high"
    assert "high" in ALLOWED_SEVERITIES


def test_args_must_be_object(registry: ToolRegistry):
    result = registry.execute("list_open_bugs", "not-a-dict")  # type: ignore[arg-type]
    assert result.ok is False
    assert result.error_code == "INVALID_ARGS"


def test_no_dynamic_registration(registry: ToolRegistry):
    registry.execute("invented_tool", {})
    assert "invented_tool" not in registry.names()
    assert registry.has_tool("invented_tool") is False


def test_reset_clears_bugs(registry: ToolRegistry):
    registry.execute(
        "create_bug",
        {"title": "T", "severity": "low", "description": "D"},
    )
    assert registry.snapshot()["bug_count"] == 1
    registry.reset()
    assert registry.snapshot()["bug_count"] == 0


def test_tool_result_to_dict(registry: ToolRegistry):
    ok = registry.execute(
        "create_bug",
        {"title": "T", "severity": "p1", "description": "D"},
    )
    d = ok.to_dict()
    assert d["ok"] is True
    assert d["tool"] == "create_bug"
    assert "data" in d

    bad = registry.execute("nope", {})
    d2 = bad.to_dict()
    assert d2["ok"] is False
    assert d2["error_code"] == "UNKNOWN_TOOL"
