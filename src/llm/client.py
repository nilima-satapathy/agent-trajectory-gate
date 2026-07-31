"""OpenAI-compatible chat client (Groq free tier by default)."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from openai import APIError, APIStatusError, OpenAI, RateLimitError

from src.config.settings import Settings, get_settings

# Smaller free-tier models first — better TPD headroom than 70B
DEFAULT_FALLBACK_MODELS = (
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
)


class LLMClientError(Exception):
    """Base client error."""

    def __init__(self, message: str, *, error_code: str = "API_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class MissingAPIKeyError(LLMClientError):
    def __init__(self, message: str = "OPENAI_API_KEY is not configured") -> None:
        super().__init__(message, error_code="MISSING_KEY")


class RateLimitClientError(LLMClientError):
    def __init__(
        self,
        message: str = "Provider rate limit (HTTP 429)",
        *,
        retry_after_s: float | None = None,
    ) -> None:
        super().__init__(message, error_code="RATE_LIMIT")
        self.retry_after_s = retry_after_s


def _parse_retry_after_seconds(message: str) -> float | None:
    """Parse Groq-style 'Please try again in 6m31.392s' if present."""
    m = re.search(
        r"try again in\s+(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?",
        message,
        flags=re.I,
    )
    if not m:
        return None
    minutes = float(m.group(1) or 0)
    seconds = float(m.group(2) or 0)
    total = minutes * 60 + seconds
    return total if total > 0 else None


@dataclass
class ChatMessage:
    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_api(self) -> dict[str, Any]:
        msg: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            msg["content"] = self.content
        if self.tool_calls is not None:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            msg["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            msg["name"] = self.name
        return msg


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0

    def add(self, other: "LLMUsage") -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens
        self.requests += other.requests


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model: str | None = None
    usage: LLMUsage = field(default_factory=LLMUsage)
    raw_assistant_message: dict[str, Any] = field(default_factory=dict)


class OpenAICompatibleClient:
    """Thin wrapper around openai.OpenAI for tool-calling chat completions."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.settings.has_llm_key:
            raise MissingAPIKeyError(
                "OPENAI_API_KEY is not configured. Set it in .env for live mode "
                "(Groq free tier: https://console.groq.com/)."
            )
        self._client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
        )
        return self._client

    def _model_candidates(self, primary: str | None) -> list[str]:
        primary = (primary or self.settings.openai_model or "").strip()
        ordered: list[str] = []
        for m in (primary, *DEFAULT_FALLBACK_MODELS):
            if m and m not in ordered:
                ordered.append(m)
        return ordered or ["llama-3.1-8b-instant"]

    def chat(
        self,
        messages: list[ChatMessage | dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_retries: int = 2,
    ) -> LLMResponse:
        client = self._ensure_client()
        api_messages = [
            m.to_api() if isinstance(m, ChatMessage) else m for m in messages
        ]
        last_rate_err: RateLimitClientError | None = None

        for model_name in self._model_candidates(model):
            kwargs: dict[str, Any] = {
                "model": model_name,
                "messages": api_messages,
                "temperature": temperature,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            for attempt in range(max_retries + 1):
                try:
                    completion = client.chat.completions.create(**kwargs)
                    return self._to_response(completion, model_name)
                except RateLimitError as exc:
                    msg = str(exc) or "Rate limit exceeded"
                    wait = _parse_retry_after_seconds(msg)
                    last_rate_err = RateLimitClientError(msg, retry_after_s=wait)
                    # Short sleep only for brief TPM blips; skip long TPD waits
                    if wait is not None and wait <= 15 and attempt < max_retries:
                        time.sleep(min(wait, 15.0))
                        continue
                    # Try next fallback model (may have separate quota)
                    break
                except APIStatusError as exc:
                    if getattr(exc, "status_code", None) == 429:
                        msg = str(exc) or "Rate limit exceeded"
                        wait = _parse_retry_after_seconds(msg)
                        last_rate_err = RateLimitClientError(msg, retry_after_s=wait)
                        if wait is not None and wait <= 15 and attempt < max_retries:
                            time.sleep(min(wait, 15.0))
                            continue
                        break
                    raise LLMClientError(str(exc), error_code="API_ERROR") from exc
                except APIError as exc:
                    raise LLMClientError(str(exc), error_code="API_ERROR") from exc
                except Exception as exc:  # pragma: no cover
                    raise LLMClientError(str(exc), error_code="API_ERROR") from exc

        if last_rate_err is not None:
            raise last_rate_err
        raise LLMClientError("LLM request failed", error_code="API_ERROR")

    def _to_response(self, completion: Any, model_name: str) -> LLMResponse:
        choice = completion.choices[0]
        message = choice.message
        tool_calls: list[dict[str, Any]] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                )

        usage = LLMUsage(requests=1)
        if completion.usage is not None:
            usage.prompt_tokens = int(completion.usage.prompt_tokens or 0)
            usage.completion_tokens = int(completion.usage.completion_tokens or 0)
            usage.total_tokens = int(
                completion.usage.total_tokens
                or (usage.prompt_tokens + usage.completion_tokens)
            )

        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": message.content,
        }
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            model=getattr(completion, "model", None) or model_name,
            usage=usage,
            raw_assistant_message=assistant_msg,
        )



def parse_tool_arguments(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text, "_parse_error": True}
    if isinstance(data, dict):
        return data
    return {"_value": data}
