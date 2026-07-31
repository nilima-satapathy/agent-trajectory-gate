"""Console package smoke (no Streamlit server)."""

from __future__ import annotations

from console.components import chip, checklist_row, esc
from console.app import run_fixture_suite, run_suite


def test_chip_html():
    html = chip("PASS", "PASS")
    # Night Circuit uses "stamp" badges, not soft chips from other apps
    assert "stamp-pass" in html
    assert "PASS" in html


def test_esc_and_checklist():
    assert "&lt;" in esc("<x>")
    row = checklist_row(True, "ok item")
    assert "mk-ok" in row
    assert "ok item" in row


def test_run_fixture_suite_quick():
    report = run_fixture_suite("quick")
    assert report["counts"]["cases"] >= 8
    assert "rows" in report
    assert report["mode"] == "fixture"


def test_run_suite_fixture_mode():
    report = run_suite("quick", mode="fixture", run_l3=False)
    assert report["mode"] == "fixture"
    assert report["counts"]["cases"] >= 8
