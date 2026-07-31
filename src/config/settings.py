"""Environment and path settings for Agent Trajectory Gate."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings loaded from environment / .env."""

    root: Path
    golden_dir: Path
    config_dir: Path
    scoring_path: Path
    reports_dir: Path
    live_runs_dir: Path
    console_dir: Path

    sut_mode: str  # fixture | live
    openai_api_key: str
    openai_base_url: str
    openai_model: str

    judge_enabled: bool
    max_tool_steps: int
    free_tier_daily_token_budget: int

    @property
    def has_llm_key(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def is_live(self) -> bool:
        return self.sut_mode == "live"

    @property
    def is_fixture(self) -> bool:
        return self.sut_mode == "fixture"


def _apply_streamlit_secrets() -> None:
    """Map Streamlit Cloud secrets → env (without overriding existing env)."""
    try:
        import streamlit as st  # type: ignore

        secrets = getattr(st, "secrets", None)
        if secrets is None:
            return
        # st.secrets supports mapping-style access
        for key in (
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "OPENAI_MODEL",
            "JUDGE_ENABLED",
            "SUT_MODE",
            "MAX_TOOL_STEPS",
            "FREE_TIER_DAILY_TOKEN_BUDGET",
        ):
            try:
                val = secrets.get(key) if hasattr(secrets, "get") else secrets[key]
            except Exception:
                continue
            if val is None:
                continue
            text = str(val).strip()
            if text and not os.getenv(key):
                os.environ[key] = text
    except Exception:
        # Not running under Streamlit or secrets unavailable
        return


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    _apply_streamlit_secrets()

    sut_mode = os.getenv("SUT_MODE", "fixture").strip().lower()

    if sut_mode not in ("fixture", "live"):
        sut_mode = "fixture"

    max_steps = _env_int("MAX_TOOL_STEPS", 6)
    if max_steps < 1:
        max_steps = 1

    budget = _env_int("FREE_TIER_DAILY_TOKEN_BUDGET", 100_000)
    if budget < 0:
        budget = 0

    reports_dir = ROOT / "reports"
    live_runs_dir = reports_dir / "live_runs"

    return Settings(
        root=ROOT,
        golden_dir=ROOT / "golden",
        config_dir=ROOT / "config",
        scoring_path=ROOT / "config" / "scoring.yaml",
        reports_dir=reports_dir,
        live_runs_dir=live_runs_dir,
        console_dir=ROOT / "console",
        sut_mode=sut_mode,
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_base_url=os.getenv(
            "OPENAI_BASE_URL", "https://api.groq.com/openai/v1"
        ).strip(),
        # Prefer 8B free-tier model — higher TPD headroom than 70B on Groq free
        openai_model=os.getenv("OPENAI_MODEL", "llama-3.1-8b-instant").strip(),
        # Default ON so free-tier key enables LLM trajectory review
        judge_enabled=_env_bool("JUDGE_ENABLED", True),


        max_tool_steps=max_steps,
        free_tier_daily_token_budget=budget,
    )


def clear_settings_cache() -> None:
    """Clear cached settings (for tests that mutate env)."""
    get_settings.cache_clear()
