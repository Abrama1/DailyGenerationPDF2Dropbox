from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.db.db import fetch_last_success_date_key, fetch_recent_runs


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _atomic_write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def export_dashboard_json(
    db_path: str,
    *,
    out_dir: str | Path = "site/data",
    runs_limit: int = 100,
) -> None:
    out_dir = Path(out_dir)
    runs = fetch_recent_runs(db_path, limit=runs_limit)
    last_run = runs[0] if runs else None

    summary = {
        "generated_at": _utc_now_iso(),
        "last_success_date_key": fetch_last_success_date_key(db_path),
        "last_run": last_run,
    }

    runs_payload = {
        "generated_at": _utc_now_iso(),
        "runs": runs,
    }

    _atomic_write_json(out_dir / "summary.json", summary)
    _atomic_write_json(out_dir / "runs.json", runs_payload)
