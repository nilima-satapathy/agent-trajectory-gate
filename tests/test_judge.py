"""L3 LLM trajectory judge (mocked — no network)."""

from __future__ import annotations

import json

from src.agent.types import AgentResult, TrajectoryStep
from src.judge.judge import judge_trajectory, run_judge
from src.judge.trajectory_judge import run_trajectory_judge
from src.llm.client import LLMResponse, LLMUsage
from src.scoring import score_run


class FakeJudgeClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.last_messages = None

    def chat(self, messages, **kwargs):  # noqa: ANN001
        self.last_messages = messages
        return LLMResponse(
            content=self.content,
            usage=LLMUsage(total_tokens=20, requests=1),
            model="judge-fake",
        )


PASS_JSON = json.dumps(
    {
        "pass": True,
        "score": 5,
        "path_ok": True,
        "primary_failure": "OK",
        "issues": [],
        "summary": "Correct tools in order with honest answer",
    }
)

FAIL_JSON = json.dumps(
    {
        "pass": False,
        "score": 1,
        "path_ok": False,
        "primary_failure": "MISSING_TOOL",
        "issues": ["create_bug never called", "invented bug id"],
        "summary": "Agent claimed create without tools",
    }
)


def test_judge_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("JUDGE_ENABLED", "false")
    from src.config.settings import clear_settings_cache

    clear_settings_cache()
    issues = run_judge({"id": "x"}, AgentResult(input="i", final_answer="a"))
    assert issues == []


def test_trajectory_judge_fail_issue(monkeypatch):
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    from src.config.settings import clear_settings_cache

    clear_settings_cache()
    client = FakeJudgeClient(FAIL_JSON)
    result = AgentResult(
        input="Create a high bug and assign web",
        final_answer="I created BUG-9999",
        trajectory=[
            TrajectoryStep(step=1, kind="final", content="I created BUG-9999"),
        ],
    )
    issues = run_judge({"id": "x", "expected": {"must_call_tools": ["create_bug"]}}, result, client=client)  # type: ignore[arg-type]
    assert len(issues) == 1
    assert issues[0].code == "TRAJECTORY_JUDGE_FAIL"
    assert "score=1" in issues[0].message


def test_trajectory_judge_pass_no_issues(monkeypatch):
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    from src.config.settings import clear_settings_cache

    clear_settings_cache()
    client = FakeJudgeClient(PASS_JSON)
    issues = run_judge(
        {"id": "x", "expected": {"must_call_tools": ["list_open_bugs"]}},
        AgentResult(
            input="list bugs",
            final_answer="Listed open bugs",
            trajectory=[
                TrajectoryStep(
                    step=1,
                    kind="tool",
                    tool="list_open_bugs",
                    args={},
                    result={"ok": True, "tool": "list_open_bugs", "data": {"count": 0}},
                ),
                TrajectoryStep(step=2, kind="final", content="Listed open bugs"),
            ],
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert issues == []


def test_trajectory_judge_sends_path_not_just_answer(monkeypatch):
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    from src.config.settings import clear_settings_cache

    clear_settings_cache()
    client = FakeJudgeClient(PASS_JSON)
    result = AgentResult(
        input="create bug",
        final_answer="done",
        trajectory=[
            TrajectoryStep(
                step=1,
                kind="tool",
                tool="create_bug",
                args={"title": "t", "severity": "high", "description": "d"},
                result={"ok": True, "data": {"bug_id": "BUG-1"}},
            ),
            TrajectoryStep(step=2, kind="final", content="done"),
        ],
    )
    v = run_trajectory_judge(
        {"id": "c1", "expected": {"must_call_tools": ["create_bug"]}},
        result,
        client=client,  # type: ignore[arg-type]
    )
    assert v.passed is True
    assert v.score == 5
    # Prompt must include trajectory structure
    user_content = client.last_messages[1]["content"]
    assert "trajectory" in user_content
    assert "create_bug" in user_content
    assert "must_call_tools" in user_content


def test_score_run_attaches_llm_fields(monkeypatch):
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from src.config.settings import clear_settings_cache

    clear_settings_cache()

    # Inject via monkeypatching run_trajectory_judge
    from src.judge import trajectory_judge as tj

    def fake_judge(case, result, **kwargs):
        from src.judge.trajectory_judge import TrajectoryJudgeVerdict

        return TrajectoryJudgeVerdict(
            passed=False,
            score=2,
            path_ok=False,
            summary="Missing create_bug on path",
            primary_failure="MISSING_TOOL",
            issues=["no create"],
        )

    monkeypatch.setattr(tj, "run_trajectory_judge", fake_judge)

    case = {
        "id": "t",
        "expected": {"must_call_tools": ["create_bug"]},
    }
    result = AgentResult(input="create", final_answer="ok", trajectory=[])
    score = score_run(case, result, run_l3=True)
    assert score.l3 is not None
    assert score.l3.status == "FAIL"
    assert score.l3_summary == "Missing create_bug on path"
    assert score.l3_score == 2
    assert score.l3_path_ok is False
    assert score.l3_primary_failure == "MISSING_TOOL"


def test_score_run_l3_skip_when_forced_off():
    case = {
        "id": "t",
        "expected": {"must_call_tools": ["list_open_bugs"]},
    }
    result = AgentResult(
        input="list",
        final_answer="listed",
        trajectory=[
            TrajectoryStep(
                step=1,
                kind="tool",
                tool="list_open_bugs",
                args={},
                result={"ok": True, "tool": "list_open_bugs", "data": {}},
            ),
            TrajectoryStep(step=2, kind="final", content="listed"),
        ],
    )
    score = score_run(case, result, run_l3=False)
    assert score.l3 is not None
    assert score.l3.status == "SKIP"
