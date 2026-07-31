"""Load and validate golden/fixture cases (no network)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from src.config.settings import get_settings

SuiteName = Literal["quick", "full"]


class CaseValidationError(ValueError):
    """Golden case failed structural validation."""


def cases_path(path: Path | None = None) -> Path:
    settings = get_settings()
    return path or (settings.golden_dir / "fixture_cases.json")


def schema_path() -> Path:
    return get_settings().golden_dir / "schema.json"


def load_fixture_cases(
    path: Path | None = None,
    *,
    tag: str | None = None,
    suite: SuiteName | None = None,
    validate: bool = True,
) -> list[dict[str, Any]]:
    """
    Load cases from golden/fixture_cases.json (or override path).

    - tag: keep cases whose tags include this value
    - suite: 'quick' => tag quick; 'full' => all cases
    - validate: structural checks (id/input/expected/fixture)
    """
    case_path = cases_path(path)
    if not case_path.is_file():
        raise FileNotFoundError(f"Fixture cases not found: {case_path}")

    raw = json.loads(case_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Expected list of cases in {case_path}")

    if suite == "quick":
        tag = "quick"
    elif suite == "full":
        tag = None

    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"Each case must be an object in {case_path}")
        if validate:
            validate_case(item)
        cid = str(item["id"])
        if cid in seen_ids:
            raise CaseValidationError(f"Duplicate case id: {cid}")
        seen_ids.add(cid)
        if tag is not None:
            tags = item.get("tags") or []
            if tag not in tags:
                continue
        cases.append(item)
    return cases


def get_case_by_id(case_id: str, path: Path | None = None) -> dict[str, Any]:
    for case in load_fixture_cases(path, validate=True):
        if case.get("id") == case_id:
            return case
    raise KeyError(f"Unknown case id: {case_id}")


def validate_case(case: dict[str, Any]) -> None:
    """Lightweight structural validation aligned with golden/schema.json."""
    for key in ("id", "input", "expected", "fixture"):
        if key not in case:
            raise CaseValidationError(f"Case missing required field: {key}")
    if not str(case["id"]).strip():
        raise CaseValidationError("Case id must be non-empty")
    if not isinstance(case["expected"], dict):
        raise CaseValidationError(f"Case {case['id']}: expected must be an object")
    fixture = case["fixture"]
    if not isinstance(fixture, dict):
        raise CaseValidationError(f"Case {case['id']}: fixture must be an object")
    if fixture.get("final_answer") is None and fixture.get("answer") is None:
        raise CaseValidationError(
            f"Case {case['id']}: fixture.final_answer (or answer) is required"
        )
    traj = fixture.get("trajectory") or fixture.get("steps") or []
    if not isinstance(traj, list):
        raise CaseValidationError(
            f"Case {case['id']}: fixture.trajectory must be a list when present"
        )


def suite_stats(path: Path | None = None) -> dict[str, Any]:
    full = load_fixture_cases(path, suite="full")
    quick = load_fixture_cases(path, suite="quick")
    by_type: dict[str, int] = {}
    for c in full:
        ct = str(c.get("case_type") or "unknown")
        by_type[ct] = by_type.get(ct, 0) + 1
    return {
        "full_count": len(full),
        "quick_count": len(quick),
        "by_case_type": dict(sorted(by_type.items())),
        "ids": [c["id"] for c in full],
        "quick_ids": [c["id"] for c in quick],
    }


def load_schema_document() -> dict[str, Any]:
    path = schema_path()
    if not path.is_file():
        raise FileNotFoundError(f"Schema not found: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("schema.json must be an object")
    return doc
