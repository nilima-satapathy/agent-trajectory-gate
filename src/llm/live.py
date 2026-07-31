"""Live Agent SUT — real free-tier tool-calling via OpenAI-compatible API."""

from __future__ import annotations

from typing import Any

from src.agent.loop import AgentLoop
from src.agent.types import AgentResult
from src.config.settings import Settings, get_settings
from src.llm.client import OpenAICompatibleClient
from src.tools.registry import ToolRegistry


class LiveAgentSUT:
    """
    Case or free-form live agent runner.

    Case shape uses the same golden `input` field as fixtures.
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry | None = None,
        client: OpenAICompatibleClient | None = None,
        settings: Settings | None = None,
        loop: AgentLoop | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.registry = registry or ToolRegistry()
        self.client = client or OpenAICompatibleClient(self.settings)
        self.loop = loop or AgentLoop(
            registry=self.registry,
            client=self.client,
            settings=self.settings,
        )

    def run(
        self,
        case: dict[str, Any] | None = None,
        *,
        user_input: str | None = None,
        save: bool = True,
        reset_store: bool = True,
    ) -> AgentResult:
        if case is not None:
            text = str(case.get("input") or case.get("question") or "")
            case_id = case.get("id")
            cid = str(case_id) if case_id is not None else None
        else:
            if user_input is None:
                raise ValueError("Provide case= or user_input=")
            text = user_input
            cid = None

        return self.loop.run(
            text,
            case_id=cid,
            reset_store=reset_store,
            save=save,
        )


def run_live_case(case: dict[str, Any], **kwargs: Any) -> AgentResult:
    return LiveAgentSUT().run(case, **kwargs)
