"""Phase 5: failure taxonomy classification (no network)."""

from __future__ import annotations

from src.llm.cases import get_case_by_id, load_fixture_cases
from src.llm.fixture import FixtureSUT
from src.scoring import classify_failure, score_run, taxonomy_counts
from src.tools import ToolRegistry


def test_ok_label_on_pass():
    case = get_case_by_id("triage-002")
    score = score_run(case, FixtureSUT().run(case))
    assert score.verdict == "PASS"
    assert score.taxonomy_label == "OK"
    assert score.taxonomy_rationale


def test_missing_tool_primary_over_answer_lie():
    case = get_case_by_id("triage-fail-missing-tool")
    score = score_run(case, FixtureSUT().run(case))
    assert score.verdict == "FAIL"
    # Both MISSING_TOOL and ANSWER_LIE present; path class wins
    codes = {i.code for i in score.issues}
    assert "MISSING_TOOL" in codes
    assert "ANSWER_LIE" in codes
    assert score.taxonomy_label == "MISSING_TOOL"
    assert "ANSWER_LIE" in score.taxonomy_secondary or "ANSWER" in str(
        score.taxonomy_secondary
    )


def test_empty_trajectory_taxonomy():
    case = get_case_by_id("triage-fail-no-tools")
    score = score_run(case, FixtureSUT().run(case))
    assert score.taxonomy_label == "MISSING_TOOL"


def test_deterministic_twice():
    case = get_case_by_id("triage-fail-missing-tool")
    result = FixtureSUT(ToolRegistry()).run(case)
    a = score_run(case, result)
    b = score_run(case, result)
    assert a.taxonomy_label == b.taxonomy_label
    assert a.taxonomy_rationale == b.taxonomy_rationale
    tax_a = classify_failure(a)
    tax_b = classify_failure(b)
    assert tax_a == tax_b


def test_hallucinated_tool_label():
    from src.agent.types import AgentResult, TrajectoryStep

    case = {"id": "h", "expected": {}}
    result = AgentResult(
        input="x",
        final_answer="ok",
        trajectory=[
            TrajectoryStep(
                step=1,
                kind="tool",
                tool="delete_production",
                args={},
                result={"ok": False, "tool": "delete_production"},
            ),
            TrajectoryStep(step=2, kind="final", content="ok"),
        ],
    )
    score = score_run(case, result)
    assert score.taxonomy_label == "HALLUCINATED_TOOL"


def test_taxonomy_counts_suite():
    sut = FixtureSUT()
    labels: list[str] = []
    for case in load_fixture_cases():
        score = score_run(case, sut.run(case))
        assert score.taxonomy_label is not None
        labels.append(score.taxonomy_label)
    counts = taxonomy_counts(labels)
    assert sum(counts.values()) == len(labels)
    assert "OK" in counts
    assert "MISSING_TOOL" in counts


def test_score_to_dict_includes_taxonomy():
    case = get_case_by_id("triage-002")
    d = score_run(case, FixtureSUT().run(case)).to_dict()
    assert d["taxonomy"]["label"] == "OK"
    assert "rationale" in d["taxonomy"]
