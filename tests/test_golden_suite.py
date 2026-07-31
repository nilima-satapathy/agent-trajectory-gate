"""Phase 6: golden suite size, schema, quick/full, offline score smoke."""

from __future__ import annotations

from collections import Counter

import pytest

from src.llm.cases import (
    CaseValidationError,
    load_fixture_cases,
    load_schema_document,
    suite_stats,
    validate_case,
)
from src.llm.fixture import FixtureSUT
from src.scoring import score_run, taxonomy_counts
from src.tools import ToolRegistry


def test_schema_document_exists():
    schema = load_schema_document()
    assert schema.get("title") == "AgentTrajectoryGateCase"
    assert "id" in schema["required"]
    assert "fixture" in schema["properties"]


def test_suite_size_requirements():
    stats = suite_stats()
    assert stats["full_count"] >= 25, stats
    assert stats["quick_count"] >= 8, stats
    assert len(stats["ids"]) == len(set(stats["ids"]))


def test_case_type_coverage():
    stats = suite_stats()
    types = set(stats["by_case_type"])
    for needed in (
        "happy_path",
        "list_only",
        "deliberate_fail",
        "adversarial",
        "multi_step",
        "edge",
        "regression",
    ):
        assert needed in types, f"missing case_type {needed}: {types}"


def test_every_case_has_fixture_trajectory_field():
    for case in load_fixture_cases(suite="full"):
        fixture = case["fixture"]
        assert "final_answer" in fixture or "answer" in fixture
        traj = fixture.get("trajectory")
        assert isinstance(traj, list)


def test_validate_case_rejects_missing_fields():
    with pytest.raises(CaseValidationError):
        validate_case({"id": "x", "input": "hi"})


def test_all_cases_run_offline_and_score():
    sut = FixtureSUT(ToolRegistry())
    labels: list[str] = []
    verdicts: list[str] = []
    for case in load_fixture_cases(suite="full"):
        result = sut.run(case)
        assert result.mode == "fixture"
        assert result.case_id == case["id"]
        score = score_run(case, result)
        assert score.taxonomy_label is not None
        labels.append(score.taxonomy_label)
        verdicts.append(score.verdict)

    counts = taxonomy_counts(labels)
    assert sum(counts.values()) >= 25
    # Suite includes deliberate passes and fails
    assert "OK" in counts
    assert any(v == "FAIL" for v in verdicts)
    assert any(v == "PASS" for v in verdicts)


def test_quick_suite_subset():
    quick = load_fixture_cases(suite="quick")
    full = load_fixture_cases(suite="full")
    assert 8 <= len(quick) < len(full)
    assert all("quick" in (c.get("tags") or []) for c in quick)


def test_expected_pass_cases_do_not_all_fail():
    """Sanity: majority of non-fail_demo cases should PASS."""
    sut = FixtureSUT(ToolRegistry())
    pass_n = fail_n = 0
    for case in load_fixture_cases(suite="full"):
        tags = case.get("tags") or []
        if "fail_demo" in tags or case.get("case_type") in (
            "deliberate_fail",
            "order_trap",
            "adversarial",
        ):
            continue
        # edge empty is pass-by-design without fail tag
        score = score_run(case, sut.run(case))
        if score.verdict == "PASS":
            pass_n += 1
        elif score.verdict == "FAIL":
            fail_n += 1
    assert pass_n >= 10, f"pass={pass_n} fail={fail_n}"


def test_fail_demo_cases_fail():
    sut = FixtureSUT(ToolRegistry())
    fail_demos = [
        c
        for c in load_fixture_cases(suite="full")
        if "fail_demo" in (c.get("tags") or [])
    ]
    assert len(fail_demos) >= 5
    for case in fail_demos:
        score = score_run(case, sut.run(case))
        assert score.verdict == "FAIL", (case["id"], score.reasons)


def test_case_type_histogram_stable():
    stats = suite_stats()
    # Keep a usable mix, not only happy paths
    assert stats["by_case_type"].get("happy_path", 0) >= 5
    assert stats["by_case_type"].get("list_only", 0) >= 2
    assert Counter(stats["by_case_type"]).total() == stats["full_count"]
