#!/usr/bin/env python3
"""Batch eval runner: fixture or live suite → reports/last_run.json."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import clear_settings_cache, get_settings
from src.llm.cases import load_fixture_cases
from src.llm.fixture import FixtureSUT
from src.scoring import score_run, taxonomy_counts
from src.tools import ToolRegistry


def run_suite(
    *,
    suite: str = "quick",
    mode: str = "fixture",
    fail_on_fail: bool = True,
    save_live: bool = True,
    run_l3: bool | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    cases = load_fixture_cases(suite="quick" if suite == "quick" else "full")

    results: list[dict[str, Any]] = []
    labels: list[str] = []
    pass_n = warn_n = fail_n = 0

    if mode == "live":
        from src.llm.live import LiveAgentSUT

        sut: Any = LiveAgentSUT(registry=ToolRegistry(), settings=settings)
    else:
        sut = FixtureSUT(ToolRegistry())

    for case in cases:
        if mode == "live":
            agent_result = sut.run(case, save=save_live)
        else:
            agent_result = sut.run(case)

        score = score_run(case, agent_result, run_l3=run_l3)
        labels.append(score.taxonomy_label or "OTHER")
        if score.verdict == "PASS":
            pass_n += 1
        elif score.verdict == "WARN":
            warn_n += 1
        else:
            fail_n += 1

        results.append(
            {
                "case_id": case.get("id"),
                "verdict": score.verdict,
                "taxonomy": score.taxonomy_label,
                "taxonomy_rationale": score.taxonomy_rationale,
                "tool_names": agent_result.tool_names,
                "latency_ms": agent_result.latency_ms,
                "mode": agent_result.mode,
                "model": agent_result.model,
                "error": agent_result.error,
                "error_code": agent_result.error_code,
                "reasons": score.reasons,
                "l1": score.l1.status,
                "l2": score.l2.status,
                "l3": score.l3.status if score.l3 else "SKIP",
                "final_answer": agent_result.final_answer,
                "trajectory": [s.to_dict() for s in agent_result.trajectory],
            }
        )

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite": suite,
        "mode": mode,
        "counts": {
            "cases": len(results),
            "PASS": pass_n,
            "WARN": warn_n,
            "FAIL": fail_n,
        },
        "taxonomy_counts": taxonomy_counts(labels),
        "results": results,
    }

    reports_dir = settings.reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "last_run.json"
    md_path = reports_dir / "last_run.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    report["report_paths"] = {"json": str(json_path), "md": str(md_path)}
    report["failed"] = fail_n > 0 and fail_on_fail
    return report


def _to_markdown(report: dict[str, Any]) -> str:
    c = report["counts"]
    lines = [
        f"# Agent Trajectory Gate — last run",
        "",
        f"- Suite: `{report['suite']}`",
        f"- Mode: `{report['mode']}`",
        f"- Generated: {report['generated_at']}",
        f"- Cases: **{c['cases']}** · PASS **{c['PASS']}** · WARN **{c['WARN']}** · FAIL **{c['FAIL']}**",
        "",
        "## Taxonomy",
        "",
    ]
    for label, n in (report.get("taxonomy_counts") or {}).items():
        lines.append(f"- `{label}`: {n}")
    lines.extend(["", "## Results", "", "| Case | Verdict | Taxonomy | Tools |", "|---|---|---|---|"])
    for r in report["results"]:
        tools = " → ".join(r.get("tool_names") or []) or "—"
        lines.append(
            f"| `{r['case_id']}` | {r['verdict']} | {r.get('taxonomy')} | {tools} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Agent Trajectory Gate eval suite")
    parser.add_argument("--suite", choices=["quick", "full"], default="quick")
    parser.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Exit 0 even when cases FAIL (still writes report)",
    )
    parser.add_argument(
        "--l3",
        action="store_true",
        help="Enable optional L3 judge for this run",
    )
    parser.add_argument(
        "--no-save-live",
        action="store_true",
        help="Do not write reports/live_runs for live mode",
    )
    args = parser.parse_args(argv)

    # Allow CLI to override mode without editing .env permanently
    import os

    if args.mode == "live":
        os.environ["SUT_MODE"] = "live"
    clear_settings_cache()

    report = run_suite(
        suite=args.suite,
        mode=args.mode,
        fail_on_fail=not args.no_fail,
        save_live=not args.no_save_live,
        run_l3=True if args.l3 else False,
    )
    c = report["counts"]
    print(
        f"Suite={report['suite']} mode={report['mode']} "
        f"PASS={c['PASS']} WARN={c['WARN']} FAIL={c['FAIL']}"
    )
    print(f"Wrote {report['report_paths']['json']}")
    print(f"Wrote {report['report_paths']['md']}")
    if report.get("failed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
