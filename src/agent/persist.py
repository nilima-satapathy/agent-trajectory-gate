"""Persist live agent runs for offline re-score / demos."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agent.types import AgentResult
from src.config.settings import get_settings


def save_live_run(
    result: AgentResult,
    *,
    directory: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    settings = get_settings()
    out_dir = directory or settings.live_runs_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    case_part = result.case_id or "adhoc"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in case_part)
    path = out_dir / f"{ts}_{safe}.json"

    payload: dict[str, Any] = result.to_dict()
    payload["saved_at"] = ts
    if extra:
        payload["extra"] = extra

    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
