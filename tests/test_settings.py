"""Phase 1: settings load correctly without network."""

from __future__ import annotations

import os

import pytest

from src.config.settings import ROOT, Settings, clear_settings_cache, get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_root_points_at_repo():
    assert (ROOT / "openspec" / "config.yaml").is_file()
    assert (ROOT / "README.md").is_file()


def test_get_settings_defaults(monkeypatch):
    # Isolate from user .env + conftest JUDGE override so code defaults are tested
    monkeypatch.setattr("src.config.settings.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("SUT_MODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JUDGE_ENABLED", raising=False)
    monkeypatch.delenv("MAX_TOOL_STEPS", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    clear_settings_cache()

    s = get_settings()
    assert isinstance(s, Settings)
    assert s.sut_mode == "fixture"
    assert s.is_fixture is True
    assert s.is_live is False
    # When JUDGE_ENABLED is unset, default is True (LLM trajectory judge on with key)
    assert s.judge_enabled is True
    assert s.max_tool_steps == 6
    assert s.has_llm_key is False
    assert "groq.com" in s.openai_base_url or s.openai_base_url
    assert s.golden_dir == ROOT / "golden"
    assert s.reports_dir == ROOT / "reports"
    assert s.live_runs_dir == ROOT / "reports" / "live_runs"
    assert s.scoring_path == ROOT / "config" / "scoring.yaml"




def test_sut_mode_live(monkeypatch):
    monkeypatch.setenv("SUT_MODE", "live")
    clear_settings_cache()
    s = get_settings()
    assert s.sut_mode == "live"
    assert s.is_live is True


def test_sut_mode_invalid_falls_back_to_fixture(monkeypatch):
    monkeypatch.setenv("SUT_MODE", "banana")
    clear_settings_cache()
    s = get_settings()
    assert s.sut_mode == "fixture"


def test_judge_enabled_true(monkeypatch):
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    clear_settings_cache()
    assert get_settings().judge_enabled is True


def test_has_llm_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "gsk_test_key")
    clear_settings_cache()
    assert get_settings().has_llm_key is True


def test_max_tool_steps_clamped(monkeypatch):
    monkeypatch.setenv("MAX_TOOL_STEPS", "0")
    clear_settings_cache()
    assert get_settings().max_tool_steps == 1


def test_package_layout_dirs_exist():
    expected = [
        ROOT / "src" / "config",
        ROOT / "src" / "tools",
        ROOT / "src" / "agent",
        ROOT / "src" / "llm",
        ROOT / "src" / "scoring",
        ROOT / "src" / "judge",
        ROOT / "golden",
        ROOT / "config",
        ROOT / "evals",
        ROOT / "console",
        ROOT / "tests",
        ROOT / "reports",
        ROOT / "docs",
        ROOT / "scripts",
    ]
    for path in expected:
        assert path.is_dir(), f"missing directory: {path}"
