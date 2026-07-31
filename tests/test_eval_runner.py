"""Phase 9: eval suite runner (fixture mode)."""

from __future__ import annotations

from evals.run_suite import run_suite


def test_run_suite_fixture_quick():
    report = run_suite(suite="quick", mode="fixture", fail_on_fail=False)
    assert report["counts"]["cases"] >= 8
    assert "PASS" in report["counts"]
    assert report["report_paths"]["json"].endswith("last_run.json")
    from pathlib import Path

    assert Path(report["report_paths"]["json"]).is_file()
    assert Path(report["report_paths"]["md"]).is_file()
    assert report["taxonomy_counts"]
