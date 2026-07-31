"""Pytest defaults: keep unit tests offline (no accidental LLM judge calls)."""

from __future__ import annotations

import pytest

from src.config.settings import clear_settings_cache
from src.scoring.config import clear_scoring_config_cache


@pytest.fixture(autouse=True)
def _offline_defaults(monkeypatch):
    """
    Disable L3 LLM trajectory judge unless a test explicitly re-enables it.
    Prevents golden-suite / scoring tests from hanging on live Groq calls.
    """
    monkeypatch.setenv("JUDGE_ENABLED", "false")
    clear_settings_cache()
    clear_scoring_config_cache()
    yield
    clear_settings_cache()
    clear_scoring_config_cache()
