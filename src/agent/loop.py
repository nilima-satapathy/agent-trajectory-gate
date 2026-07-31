"""Multi-step tool-calling agent loop (live)."""

from __future__ import annotations

import time
from typing import Any

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.types import AgentResult, TrajectoryStep
from src.config.settings import Settings, get_settings
from src.llm.client import (
    LLMClientError,
    MissingAPIKeyError,
    OpenAICompatibleClient,
    RateLimitClientError,
    parse_tool_arguments,
)
from src.meter.free_tier import FreeTierMeter, get_meter
from src.tools.registry import ToolRegistry


class AgentLoop:
    """Run user input through LLM tool-calling until final answer or max steps."""

    def __init__(
        self,
        *,
        registry: ToolRegistry | None = None,
        client: OpenAICompatibleClient | None = None,
        settings: Settings | None = None,
        meter: FreeTierMeter | None = None,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.settings = settings or get_settings()
        self.registry = registry or ToolRegistry()
        self.client = client or OpenAICompatibleClient(self.settings)
        self.meter = meter or get_meter()
        self.system_prompt = system_prompt

    def run(
        self,
        user_input: str,
        *,
        case_id: str | None = None,
        reset_store: bool = True,
        save: bool = False,
    ) -> AgentResult:
        t0 = time.perf_counter()
        if reset_store:
            self.registry.reset()

        max_steps = self.settings.max_tool_steps
        tools = self.registry.tool_schemas()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]

        trajectory: list[TrajectoryStep] = []
        step_i = 0
        final_answer = ""
        model_name: str | None = self.settings.openai_model
        max_steps_hit = False
        error: str | None = None
        error_code: str | None = None

        try:
            for _round in range(max_steps):
                resp = self.client.chat(messages, tools=tools)
                self.meter.record_agent(resp.usage)
                model_name = resp.model or model_name
                messages.append(resp.raw_assistant_message)

                if resp.tool_calls:
                    for tc in resp.tool_calls:
                        step_i += 1
                        fn = tc.get("function") or {}
                        name = str(fn.get("name") or "")
                        args = parse_tool_arguments(fn.get("arguments"))
                        # If parse failed, still execute with empty/invalid → structured error
                        if args.get("_parse_error"):
                            tool_result = self.registry.execute(name, {})
                            # override message
                            from src.tools.registry import ToolResult

                            tool_result = ToolResult(
                                ok=False,
                                tool=name or "unknown",
                                error="Failed to parse tool arguments as JSON",
                                error_code="VALIDATION_ERROR",
                            )
                        else:
                            clean_args = {
                                k: v
                                for k, v in args.items()
                                if not str(k).startswith("_")
                            }
                            tool_result = self.registry.execute(name, clean_args)

                        result_dict = tool_result.to_dict()
                        trajectory.append(
                            TrajectoryStep(
                                step=step_i,
                                kind="tool",
                                tool=name or None,
                                args={
                                    k: v
                                    for k, v in args.items()
                                    if not str(k).startswith("_")
                                }
                                if not args.get("_parse_error")
                                else {"_raw": args.get("_raw")},
                                result=result_dict,
                            )
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.get("id") or f"call_{step_i}",
                                "content": _json_content(result_dict),
                            }
                        )
                    continue

                # Final text response
                final_answer = (resp.content or "").strip()
                break
            else:
                # exhausted max rounds still requesting tools
                max_steps_hit = True
                final_answer = final_answer or (
                    "Stopped: reached maximum tool-calling steps without a final answer."
                )

        except MissingAPIKeyError as exc:
            error = str(exc)
            error_code = exc.error_code
            final_answer = ""
        except RateLimitClientError as exc:
            error = str(exc)
            error_code = exc.error_code
            final_answer = final_answer or "Provider rate limit exceeded. Try again later."
        except LLMClientError as exc:
            error = str(exc)
            error_code = exc.error_code
            final_answer = final_answer or f"Model error: {exc}"

        step_i += 1
        trajectory.append(
            TrajectoryStep(step=step_i, kind="final", content=final_answer)
        )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        meta: dict[str, Any] = {
            "max_tool_steps": max_steps,
            "max_steps_hit": max_steps_hit,
            "meter": self.meter.to_dict(),
        }
        if max_steps_hit and not error_code:
            error_code = "MAX_STEPS"

        result = AgentResult(
            input=user_input,
            final_answer=final_answer,
            trajectory=trajectory,
            mode="live",
            case_id=case_id,
            store_snapshot=self.registry.snapshot(),
            latency_ms=latency_ms,
            model=model_name,
            error=error,
            error_code=error_code,
            meta=meta,
        )

        if save:
            from src.agent.persist import save_live_run

            path = save_live_run(result)
            result.meta["saved_path"] = str(path)

        return result


def _json_content(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, ensure_ascii=False)
