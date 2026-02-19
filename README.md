# PDF → Dropbox Daily Uploader (YYYYMMDD)

A small automation that:
- Downloads a PDF from a fixed URL once per day.
- Extracts a Georgian date from the PDF text.
- Converts it to a `YYYYMMDD` key (e.g., `20260217`).
- Uploads the PDF to Dropbox as `/Reports/YYYYMMDD.pdf` if it hasn’t been processed before.
- Logs runs + processed dates in SQLite.
- Exports JSON logs for a simple GitHub Pages dashboard.

## Key Rules

- **Date key format:** `YYYYMMDD`
- **Dropbox target filename:** `YYYYMMDD.pdf`
- **No same-date versions**: one file per date key
- **Run schedule:** daily at **23:00 Asia/Tbilisi** (GitHub Actions cron uses UTC)

