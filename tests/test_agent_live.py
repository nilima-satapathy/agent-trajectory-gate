"""Phase 7: live agent loop with mocked LLM (no network by default)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.agent.loop import AgentLoop
from src.agent.persist import save_live_run
from src.agent.types import AgentResult
from src.config.settings import clear_settings_cache, get_settings
from src.llm.client import (
    LLMResponse,
    LLMUsage,
    MissingAPIKeyError,
    OpenAICompatibleClient,
    RateLimitClientError,
    parse_tool_arguments,
)
from src.llm.live import LiveAgentSUT
from src.meter.free_tier import reset_meter
from src.tools import ToolRegistry


class FakeClient:
    """Scripted tool-calling responses."""

    def __init__(self, script: list[LLMResponse]) -> None:
        self.script = list(script)
        self.calls = 0

    def chat(self, messages, *, tools=None, model=None, temperature=0.2):  # noqa: ANN001
        if self.calls >= len(self.script):
            return LLMResponse(content="fallback done", tool_calls=[], model="fake")
        resp = self.script[self.calls]
        self.calls += 1
        return resp


def _tool_call(name: str, args: dict[str, Any], call_id: str = "c1") -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def _assistant_with_tools(tool_calls: list[dict[str, Any]]) -> LLMResponse:
    return LLMResponse(
        content=None,
        tool_calls=tool_calls,
        model="fake-model",
        usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, requests=1),
        raw_assistant_message={
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        },
    )


def _final(text: str) -> LLMResponse:
    return LLMResponse(
        content=text,
        tool_calls=[],
        model="fake-model",
        usage=LLMUsage(prompt_tokens=5, completion_tokens=8, total_tokens=13, requests=1),
        raw_assistant_message={"role": "assistant", "content": text},
    )


@pytest.fixture(autouse=True)
def _reset():
    clear_settings_cache()
    reset_meter(100000)
    yield
    clear_settings_cache()
    reset_meter(100000)


def test_parse_tool_arguments():
    assert parse_tool_arguments('{"a": 1}') == {"a": 1}
    assert parse_tool_arguments(None) == {}
    bad = parse_tool_arguments("not-json")
    assert bad.get("_parse_error") is True


def test_agent_loop_create_and_assign():
    create = _assistant_with_tools(
        [
            _tool_call(
                "create_bug",
                {
                    "title": "Login fail",
                    "severity": "high",
                    "description": "Chrome",
                },
                "c1",
            )
        ]
    )
    # Second model turn: need assign — but bug_id unknown until after first tool.
    # Script assign with placeholder replaced by inspecting registry in custom client.
    registry = ToolRegistry()
    meter = reset_meter()

    class SequentialClient:
        def __init__(self) -> None:
            self.n = 0

        def chat(self, messages, **kwargs):  # noqa: ANN001
            self.n += 1
            if self.n == 1:
                return create
            if self.n == 2:
                # Read last tool result bug id from messages
                bug_id = "BUG-1001"
                for m in reversed(messages):
                    if m.get("role") == "tool":
                        data = json.loads(m["content"])
                        if data.get("data", {}).get("bug_id"):
                            bug_id = data["data"]["bug_id"]
                            break
                tc = _tool_call(
                    "assign_owner",
                    {"bug_id": bug_id, "team": "web"},
                    "c2",
                )
                return _assistant_with_tools([tc])
            return _final(f"Created ticket and assigned to web.")

    loop = AgentLoop(
        registry=registry,
        client=SequentialClient(),  # type: ignore[arg-type]
        meter=meter,
    )
    result = loop.run(
        "Create high login bug and assign web",
        case_id="live-unit-1",
        save=False,
    )
    assert result.mode == "live"
    assert result.error is None
    assert "create_bug" in result.tool_names
    assert "assign_owner" in result.tool_names
    assert result.store_snapshot["bug_count"] == 1
    assert result.trajectory[-1].kind == "final"
    assert meter.agent_requests >= 2


def test_missing_api_key_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    clear_settings_cache()
    client = OpenAICompatibleClient(get_settings())
    with pytest.raises(MissingAPIKeyError):
        client.chat([{"role": "user", "content": "hi"}])


def test_agent_loop_missing_key_returns_result(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    clear_settings_cache()
    settings = get_settings()
    loop = AgentLoop(
        registry=ToolRegistry(),
        client=OpenAICompatibleClient(settings),
        settings=settings,
    )
    result = loop.run("hi", save=False)
    assert result.error_code == "MISSING_KEY"
    assert result.mode == "live"


def test_max_steps_hit():
    # Always request tools
    forever = _assistant_with_tools(
        [_tool_call("list_open_bugs", {}, "cx")]
    )
    client = FakeClient([forever] * 20)
    from src.config.settings import Settings
    from pathlib import Path

    # tiny max steps via monkeypatched settings object
    base = get_settings()
    settings = Settings(
        root=base.root,
        golden_dir=base.golden_dir,
        config_dir=base.config_dir,
        scoring_path=base.scoring_path,
        reports_dir=base.reports_dir,
        live_runs_dir=base.live_runs_dir,
        console_dir=base.console_dir,
        sut_mode="live",
        openai_api_key="x",
        openai_base_url=base.openai_base_url,
        openai_model="m",
        judge_enabled=False,
        max_tool_steps=2,
        free_tier_daily_token_budget=1000,
    )
    loop = AgentLoop(
        registry=ToolRegistry(),
        client=client,  # type: ignore[arg-type]
        settings=settings,
        meter=reset_meter(1000),
    )
    result = loop.run("list forever", save=False)
    assert result.meta.get("max_steps_hit") is True
    assert result.error_code == "MAX_STEPS"


def test_save_live_run(tmp_path):
    result = AgentResult(
        input="x",
        final_answer="y",
        mode="live",
        case_id="save-me",
        trajectory=[],
    )
    path = save_live_run(result, directory=tmp_path)
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["case_id"] == "save-me"
    assert data["final_answer"] == "y"


def test_live_sut_with_fake_client():
    client = FakeClient(
        [
            _assistant_with_tools([_tool_call("list_open_bugs", {"severity": "high"})]),
            _final("Listed high bugs."),
        ]
    )
    sut = LiveAgentSUT(registry=ToolRegistry(), client=client)  # type: ignore[arg-type]
    # LiveAgentSUT builds its own loop with client — need to inject loop
    loop = AgentLoop(registry=ToolRegistry(), client=client)  # type: ignore[arg-type]
    sut = LiveAgentSUT(loop=loop)
    case = {
        "id": "triage-002",
        "input": "Just list open high-severity bugs.",
    }
    result = sut.run(case, save=False)
    assert result.case_id == "triage-002"
    assert result.tool_names == ["list_open_bugs"]


def test_rate_limit_maps_to_result():
    class RLClient:
        def chat(self, *a, **k):
            raise RateLimitClientError("429 too many")

    loop = AgentLoop(registry=ToolRegistry(), client=RLClient())  # type: ignore[arg-type]
    result = loop.run("hi", save=False)
    assert result.error_code == "RATE_LIMIT"


@pytest.mark.live
def test_live_smoke_groq():
    """Requires OPENAI_API_KEY (Groq). Skipped in default CI."""
    clear_settings_cache()
    settings = get_settings()
    if not settings.has_llm_key:
        pytest.skip("OPENAI_API_KEY not set")

    from src.llm.live import LiveAgentSUT

    sut = LiveAgentSUT(settings=settings)
    result = sut.run(
        user_input="List open high severity bugs only. Do not create any tickets.",
        save=True,
    )
    assert result.mode == "live"
    assert result.error_code not in ("MISSING_KEY",)
    # Soft assertion: either tools used or a textual answer
    assert result.final_answer or result.tool_names
