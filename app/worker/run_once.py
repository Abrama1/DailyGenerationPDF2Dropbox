from __future__ import annotations

import os
import tempfile
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable, Protocol

from app.config import Settings, get_settings
from app.db.db import RunFinish, create_run, finish_run, init_db, is_processed, mark_processed

from app.worker.downloader import DownloadError, download_pdf
from app.worker.dropbox_client import (
    DropboxAuthFailed,
    DropboxClient,
    DropboxClientError,
    DropboxUploadConflict,
)
from app.worker.pdf_date import DateParseError, parse_date_key_from_text
from app.worker.pdf_text import PdfTextExtractError, extract_text_from_pdf


class DropboxLike(Protocol):
    def exists(self, path: str) -> bool: ...
    def upload_new(self, local_path: str | Path, dropbox_path: str) -> None: ...


@dataclass(frozen=True)
class LockBusy(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _duration_ms(t0: float, t1: float) -> int:
    return int((t1 - t0) * 1000)


def _lock_path_for(db_path: str) -> Path:
    safe = str(abs(hash(Path(db_path).resolve().as_posix())))
    return Path(tempfile.gettempdir()) / f"dailypdf2dropbox_{safe}.lock"


def _acquire_lock(lock_path: Path) -> int:
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    try:
        fd = os.open(str(lock_path), flags)
        os.write(fd, str(os.getpid()).encode("utf-8"))
        return fd
    except FileExistsError as e:
        raise LockBusy(f"Another run is in progress (lock: {lock_path})") from e


def _release_lock(fd: int, lock_path: Path) -> None:
    try:
        os.close(fd)
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass


def run_once(
    settings: Settings,
    *,
    dbx: DropboxLike | None = None,
    download_fn: Callable[..., Path] = download_pdf,
    extract_text_fn: Callable[..., str] = extract_text_from_pdf,
    parse_date_fn: Callable[[str], str] = parse_date_key_from_text,
) -> RunFinish:
    """
    Executes one full check/upload cycle.
    Does NOT create/finish a `runs` DB row — main() handles that.
    """
    init_db(settings.db_path)

    lock_path = _lock_path_for(settings.db_path)
    lock_fd: int | None = None

    try:
        lock_fd = _acquire_lock(lock_path)

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            local_pdf = td_path / "download.pdf"

            # 1) Download
            try:
                download_fn(settings.source_pdf_url, local_pdf)
            except DownloadError as e:
                return RunFinish(
                    status="download_error",
                    stop_reason="Download failed",
                    error_message=str(e),
                )

            # 2) Extract text
            try:
                text = extract_text_fn(local_pdf, pages=(0, 1))
            except PdfTextExtractError as e:
                return RunFinish(
                    status="pdf_extract_error",
                    stop_reason="PDF text extraction failed",
                    error_message=str(e),
                )

            # 3) Parse date_key
            try:
                date_key = parse_date_fn(text)
            except DateParseError as e:
                snippet = " ".join((text or "").split())[:300]
                return RunFinish(
                    status="date_parse_error",
                    stop_reason="Could not parse date from PDF text",
                    error_message=f"{e} | snippet: {snippet}",
                )

            dropbox_path = settings.dropbox_pdf_path(date_key)

            # 4) DB dedupe
            if is_processed(settings.db_path, date_key=date_key):
                return RunFinish(
                    status="duplicate_db",
                    date_key=date_key,
                    dropbox_path=dropbox_path,
                    stop_reason="Already processed (SQLite)",
                )

            # 5) Dropbox check/upload
            client: DropboxLike = dbx if dbx is not None else DropboxClient(settings.dropbox_access_token)

            try:
                if client.exists(dropbox_path):
                    mark_processed(
                        settings.db_path,
                        date_key=date_key,
                        dropbox_path=dropbox_path,
                        processed_at=_utc_now_iso(),
                        source_url=settings.source_pdf_url,
                    )
                    return RunFinish(
                        status="duplicate_dropbox",
                        date_key=date_key,
                        dropbox_path=dropbox_path,
                        stop_reason="File already exists in Dropbox",
                    )

                client.upload_new(local_pdf, dropbox_path)

            except DropboxUploadConflict:
                mark_processed(
                    settings.db_path,
                    date_key=date_key,
                    dropbox_path=dropbox_path,
                    processed_at=_utc_now_iso(),
                    source_url=settings.source_pdf_url,
                )
                return RunFinish(
                    status="duplicate_dropbox",
                    date_key=date_key,
                    dropbox_path=dropbox_path,
                    stop_reason="Dropbox upload conflict (already exists)",
                )
            except DropboxAuthFailed as e:
                return RunFinish(
                    status="dropbox_auth_error",
                    date_key=date_key,
                    dropbox_path=dropbox_path,
                    stop_reason="Dropbox authentication failed",
                    error_message=str(e),
                )
            except DropboxClientError as e:
                return RunFinish(
                    status="dropbox_error",
                    date_key=date_key,
                    dropbox_path=dropbox_path,
                    stop_reason="Dropbox API error",
                    error_message=str(e),
                )

            # 6) Mark processed
            mark_processed(
                settings.db_path,
                date_key=date_key,
                dropbox_path=dropbox_path,
                processed_at=_utc_now_iso(),
                source_url=settings.source_pdf_url,
            )

            return RunFinish(
                status="uploaded",
                date_key=date_key,
                dropbox_path=dropbox_path,
                stop_reason="Uploaded successfully",
            )

    except LockBusy as e:
        return RunFinish(
            status="lock_busy",
            stop_reason="Skipped because another run is in progress",
            error_message=str(e),
        )
    except Exception as e:
        return RunFinish(
            status="unexpected_error",
            stop_reason="Unexpected failure",
            error_message=str(e),
            error_trace=traceback.format_exc(),
        )
    finally:
        if lock_fd is not None:
            _release_lock(lock_fd, lock_path)


def main() -> None:
    settings = get_settings()
    init_db(settings.db_path)

    t0 = perf_counter()
    run_id = create_run(settings.db_path, started_at=_utc_now_iso(), source_url=settings.source_pdf_url)

    try:
        result = run_once(settings)
    except Exception as e:
        result = RunFinish(
            status="unexpected_error",
            stop_reason="Unexpected failure",
            error_message=str(e),
            error_trace=traceback.format_exc(),
        )

    finish_run(
        settings.db_path,
        run_id=run_id,
        finished_at=_utc_now_iso(),
        duration_ms=_duration_ms(t0, perf_counter()),
        result=result,
    )

    msg = f"{result.status}"
    if result.date_key:
        msg += f" date_key={result.date_key}"
    if result.stop_reason:
        msg += f" reason='{result.stop_reason}'"
    print(msg)


if __name__ == "__main__":
    main()
