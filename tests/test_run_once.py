from __future__ import annotations

from pathlib import Path
import tempfile

from app.config import Settings
from app.db.db import init_db, is_processed, mark_processed
from app.worker.run_once import run_once


class FakeDropbox:
    def __init__(self, *, exists: bool):
        self._exists = exists
        self.exists_calls = 0
        self.upload_calls = 0
        self.uploaded_to: str | None = None

    def exists(self, path: str) -> bool:
        self.exists_calls += 1
        return self._exists

    def upload_new(self, local_path: str | Path, dropbox_path: str) -> None:
        self.upload_calls += 1
        self.uploaded_to = dropbox_path


def _stub_download(url: str, dest_path: Path, *args, **kwargs) -> Path:
    dest_path.write_bytes(b"%PDF-1.7\n%%EOF\n")
    return dest_path


def _stub_extract_text(pdf_path: Path, *args, **kwargs) -> str:
    return "თებერვალი, 2026\n17 თებერვალი"


def test_skips_if_already_processed_in_db():
    with tempfile.TemporaryDirectory() as td:
        db_path = str(Path(td) / "app.sqlite")
        init_db(db_path)

        # Pre-mark processed
        mark_processed(
            db_path,
            date_key="20260217",
            dropbox_path="/Reports/20260217.pdf",
            processed_at="2026-02-20T00:00:00+00:00",
            source_url="https://example.com/report.pdf",
        )

        settings = Settings(
            source_pdf_url="https://example.com/report.pdf",
            dropbox_access_token="x",
            dropbox_target_folder="/Reports",
            db_path=db_path,
        )

        fake = FakeDropbox(exists=False)

        res = run_once(
            settings,
            dbx=fake,
            download_fn=_stub_download,
            extract_text_fn=_stub_extract_text,
        )

        assert res.status == "duplicate_db"
        assert res.date_key == "20260217"
        assert fake.exists_calls == 0
        assert fake.upload_calls == 0


def test_uploads_and_marks_processed_when_new():
    with tempfile.TemporaryDirectory() as td:
        db_path = str(Path(td) / "app.sqlite")
        init_db(db_path)

        settings = Settings(
            source_pdf_url="https://example.com/report.pdf",
            dropbox_access_token="x",
            dropbox_target_folder="/Reports",
            db_path=db_path,
        )

        fake = FakeDropbox(exists=False)

        res = run_once(
            settings,
            dbx=fake,
            download_fn=_stub_download,
            extract_text_fn=_stub_extract_text,
        )

        assert res.status == "uploaded"
        assert res.date_key == "20260217"
        assert fake.exists_calls == 1
        assert fake.upload_calls == 1
        assert fake.uploaded_to == "/Reports/20260217.pdf"
        assert is_processed(db_path, date_key="20260217") is True


def test_skips_and_marks_processed_if_dropbox_already_has_file():
    with tempfile.TemporaryDirectory() as td:
        db_path = str(Path(td) / "app.sqlite")
        init_db(db_path)

        settings = Settings(
            source_pdf_url="https://example.com/report.pdf",
            dropbox_access_token="x",
            dropbox_target_folder="/Reports",
            db_path=db_path,
        )

        fake = FakeDropbox(exists=True)

        res = run_once(
            settings,
            dbx=fake,
            download_fn=_stub_download,
            extract_text_fn=_stub_extract_text,
        )

        assert res.status == "duplicate_dropbox"
        assert res.date_key == "20260217"
        assert fake.exists_calls == 1
        assert fake.upload_calls == 0
        assert is_processed(db_path, date_key="20260217") is True
