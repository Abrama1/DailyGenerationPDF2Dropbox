from __future__ import annotations

import json
from pathlib import Path
import tempfile

from app.db.db import RunFinish, create_run, finish_run, init_db, mark_processed
from app.worker.dashboard_export import export_dashboard_json


def test_exports_summary_and_runs_json():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        db_path = str(td_path / "app.sqlite")
        out_dir = td_path / "site" / "data"

        init_db(db_path)

        run_id = create_run(db_path, started_at="2026-02-21T19:00:00+00:00", source_url="x")
        finish_run(
            db_path,
            run_id=run_id,
            finished_at="2026-02-21T19:00:01+00:00",
            duration_ms=1000,
            result=RunFinish(status="uploaded", date_key="20260217", stop_reason="ok", dropbox_path="/Reports/20260217.pdf"),
        )

        mark_processed(
            db_path,
            date_key="20260217",
            dropbox_path="/Reports/20260217.pdf",
            processed_at="2026-02-21T19:00:01+00:00",
            source_url="x",
        )

        export_dashboard_json(db_path, out_dir=out_dir, runs_limit=50)

        summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
        runs = json.loads((out_dir / "runs.json").read_text(encoding="utf-8"))

        assert "generated_at" in summary
        assert summary["last_success_date_key"] == "20260217"
        assert summary["last_run"]["status"] == "uploaded"

        assert "runs" in runs
        assert len(runs["runs"]) >= 1
