CREATE TABLE IF NOT EXISTS processed_reports (
  date_key      TEXT PRIMARY KEY,         -- YYYYMMDD (e.g., 20260217)
  dropbox_path  TEXT NOT NULL,            -- /Reports/20260217.pdf
  processed_at  TEXT NOT NULL,            -- ISO timestamp (UTC)
  source_url    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at    TEXT NOT NULL,            -- ISO timestamp (UTC)
  finished_at   TEXT,                     -- ISO timestamp (UTC)
  duration_ms   INTEGER,
  status        TEXT NOT NULL,            -- running/uploaded/duplicate_db/...
  date_key      TEXT,                     -- YYYYMMDD (nullable)
  stop_reason   TEXT,                     -- human-friendly reason (nullable)
  error_message TEXT,                     -- short error (nullable)
  error_trace   TEXT,                     -- long trace (nullable)
  source_url    TEXT,                     -- optional traceability
  dropbox_path  TEXT                      -- optional traceability
);

CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_date_key ON runs(date_key);