from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class RunFinish:
    status: str
    date_key: str | None = None
    stop_reason: str | None = None
    error_message: str | None = None
    error_trace: str | None = None
    dropbox_path: str | None = None


def _ensure_parent_dir(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def connect(db_path: str) -> sqlite3.Connection:
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Good defaults for reliability:
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db(db_path: str) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    schema_sql = schema_path.read_text(encoding="utf-8")

    with connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()


def create_run(db_path: str, *, started_at: str, source_url: str | None = None) -> int:
    """
    Inserts a run row with status=running and returns run_id.
    """
    with connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO runs (started_at, status, source_url)
            VALUES (?, 'running', ?)
            """,
            (started_at, source_url),
        )
        conn.commit()
        return int(cur.lastrowid)


def finish_run(
    db_path: str,
    *,
    run_id: int,
    finished_at: str,
    duration_ms: int,
    result: RunFinish,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE runs
            SET finished_at = ?,
                duration_ms = ?,
                status = ?,
                date_key = ?,
                stop_reason = ?,
                error_message = ?,
                error_trace = ?,
                dropbox_path = ?
            WHERE id = ?
            """,
            (
                finished_at,
                duration_ms,
                result.status,
                result.date_key,
                result.stop_reason,
                result.error_message,
                result.error_trace,
                result.dropbox_path,
                run_id,
            ),
        )
        conn.commit()


def is_processed(db_path: str, *, date_key: str) -> bool:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_reports WHERE date_key = ? LIMIT 1",
            (date_key,),
        ).fetchone()
        return row is not None


def mark_processed(
    db_path: str,
    *,
    date_key: str,
    dropbox_path: str,
    processed_at: str,
    source_url: str,
) -> None:
    """
    Records a successfully processed date_key.
    Uses INSERT OR IGNORE to be safe in rare duplicate situations.
    """
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO processed_reports
              (date_key, dropbox_path, processed_at, source_url)
            VALUES (?, ?, ?, ?)
            """,
            (date_key, dropbox_path, processed_at, source_url),
        )
        conn.commit()


def fetch_recent_runs(db_path: str, *, limit: int = 50) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, started_at, finished_at, duration_ms, status,
                   date_key, stop_reason, error_message, dropbox_path
            FROM runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_last_success_date_key(db_path: str) -> str | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT date_key
            FROM processed_reports
            ORDER BY processed_at DESC
            LIMIT 1
            """
        ).fetchone()
        return str(row["date_key"]) if row else None
