from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx


@dataclass(frozen=True)
class DownloadError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def _looks_like_pdf(content: bytes) -> bool:
    # Most PDFs start with "%PDF"
    return content.startswith(b"%PDF")


def download_pdf(
    url: str,
    dest_path: str | Path,
    *,
    timeout_seconds: float = 30.0,
    max_retries: int = 1,
) -> Path:
    """
    Download a PDF from `url` and save it to `dest_path`.

    - Retries on transient network errors and 5xx responses.
    - Validates content looks like a PDF (starts with %PDF).
    - Writes atomically: downloads to .part then renames.

    Returns the final Path on success.
    Raises DownloadError on failure.
    """
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    timeout = httpx.Timeout(timeout_seconds)
    last_err: Optional[str] = None

    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        for attempt in range(max_retries + 1):
            try:
                resp = client.get(url)
                status = resp.status_code

                # Retry on 5xx
                if 500 <= status <= 599:
                    last_err = f"Server error {status}"
                    continue

                if status != 200:
                    raise DownloadError(f"Failed to download PDF (HTTP {status})")

                content = resp.content or b""
                if not content:
                    raise DownloadError("Downloaded file is empty")

                # Content-type check is not always reliable; header may be missing/wrong
                # But if it exists and clearly isn't PDF, fail fast.
                ctype = (resp.headers.get("content-type") or "").lower()
                if ctype and ("pdf" not in ctype):
                    # still allow if bytes look like pdf
                    if not _looks_like_pdf(content):
                        raise DownloadError(f"Unexpected content-type: {ctype}")

                if not _looks_like_pdf(content):
                    raise DownloadError("Downloaded content does not look like a PDF")

                tmp_path.write_bytes(content)
                tmp_path.replace(dest_path)
                return dest_path

            except httpx.RequestError as e:
                last_err = f"Network error: {e}"
                continue

    raise DownloadError(f"Failed to download PDF after retries. Last error: {last_err}")
