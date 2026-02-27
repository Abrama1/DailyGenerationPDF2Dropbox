# DailyGenerationPDF2Dropbox

Automates a daily workflow:

1. Downloads a PDF from a fixed URL
2. Extracts the report date from the PDF text (Georgian month/day format)
3. Converts it to a `YYYYMMDD` key (example: `20260219`)
4. Checks Dropbox + local SQLite state to avoid duplicates
5. Uploads the PDF to Dropbox as `YYYYMMDD.pdf`
6. Logs everything to SQLite and exports JSON for a static dashboard

The project runs on **GitHub Actions** (scheduled daily) and the dashboard is served via **GitHub Pages**.

---

## What it does

- **Input:** a single (fixed) PDF URL that changes its content over time
- **Extracted date format inside PDF (expected):**
  - Header contains: `თებერვალი, 2026` (month + year)
  - Table contains: `17 თებერვალი` (day + month)
- **Output file name:** `YYYYMMDD.pdf` (example: `20260219.pdf`)
- **Dropbox target:** an existing folder you control (example: `/Renovis/DailyGenerationPDF2Dropbox`)
- **Dedupe logic:**
  - If `date_key` is already recorded in SQLite → stop (`duplicate_db`)
  - Else if the file already exists in Dropbox → stop (`duplicate_dropbox`) and mark processed in SQLite
  - Else upload to Dropbox → record as processed (`uploaded`)

---

## Project structure

```text
app/
  config.py             # Environment config + validation
db/
  schema.sql            # SQLite schema
  db.py                 # SQLite helpers
worker/
  run_once.py           # Main pipeline entrypoint
  downloader.py         # PDF download (httpx)
  pdf_text.py           # PDF text extraction (PyMuPDF)
  pdf_date.py           # Georgian date parsing -> YYYYMMDD
  dropbox_client.py     # Dropbox exists/upload wrapper
  dashboard_export.py   # Exports JSON for dashboard
site/
  index.html            # Static dashboard
  styles.css
  app.js
data/
  summary.json          # Generated
  runs.json             # Generated
  app.sqlite            # SQLite state/history (updated by workflow)
tests/
  ...                   # Unit tests
.github/
  workflows/
    daily_run.yml       # Scheduled run + commit updated state
    pages.yml           # Deploy dashboard to GitHub Pages

```

---

## Requirements

- Python **3.11+**
- Dropbox developer app with permissions:
  - `files.metadata.read`
  - `files.content.write`

Python dependencies are in `requirements.txt`.

---

## Environment variables

### Required (all environments)
- `SOURCE_PDF_URL`  
  The fixed URL to download the PDF from.
- `DROPBOX_TARGET_FOLDER`  
  Dropbox folder path where the PDF files will be uploaded (example: `/Renovis/DailyGenerationPDF2Dropbox`).
- `DB_PATH`  
  Path to SQLite file (default: `data/app.sqlite`)

### Dropbox authentication (recommended: refresh token)
- `DROPBOX_APP_KEY`
- `DROPBOX_APP_SECRET`
- `DROPBOX_REFRESH_TOKEN`

### Optional fallback (short-lived token)
- `DROPBOX_ACCESS_TOKEN`  
  Not recommended for long-running automation, because it expires.

---

## Local setup

### 1) Create a virtual environment and install deps

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt

  
