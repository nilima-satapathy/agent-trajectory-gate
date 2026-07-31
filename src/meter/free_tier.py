"""Session free-tier usage tracking for live LLM calls."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.config.settings import get_settings
from src.llm.client import LLMUsage


@dataclass
class FreeTierMeter:
    budget_tokens: int
    usage: LLMUsage = field(default_factory=LLMUsage)
    judge_requests: int = 0
    agent_requests: int = 0

    def record_agent(self, usage: LLMUsage) -> None:
        self.usage.add(usage)
        self.agent_requests += usage.requests

    def record_judge(self, usage: LLMUsage) -> None:
        self.usage.add(usage)
        self.judge_requests += usage.requests

    @property
    def total_tokens(self) -> int:
        return self.usage.total_tokens

    @property
    def total_requests(self) -> int:
        return self.usage.requests

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.budget_tokens - self.total_tokens)

    @property
    def used_fraction(self) -> float:
        if self.budget_tokens <= 0:
            return 0.0
        return min(1.0, self.total_tokens / float(self.budget_tokens))

    def to_dict(self) -> dict:
        return {
            "budget_tokens": self.budget_tokens,
            "total_tokens": self.total_tokens,
            "remaining_tokens": self.remaining_tokens,
            "used_fraction": round(self.used_fraction, 4),
            "total_requests": self.total_requests,
            "agent_requests": self.agent_requests,
            "judge_requests": self.judge_requests,
            "prompt_tokens": self.usage.prompt_tokens,
            "completion_tokens": self.usage.completion_tokens,
        }


_meter: FreeTierMeter | None = None


def get_meter() -> FreeTierMeter:
    global _meter
    if _meter is None:
        budget = get_settings().free_tier_daily_token_budget
        _meter = FreeTierMeter(budget_tokens=budget)
    return _meter


def reset_meter(budget: int | None = None) -> FreeTierMeter:
    global _meter
    b = budget if budget is not None else get_settings().free_tier_daily_token_budget
    _meter = FreeTierMeter(budget_tokens=b)
    return _meter
