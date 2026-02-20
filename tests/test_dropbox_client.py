from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

import app.worker.dropbox_client as dbc


class FakePathError:
    def __init__(self, *, not_found: bool = False):
        self._not_found = not_found

    def is_not_found(self) -> bool:
        return self._not_found


class FakeMetaError:
    def __init__(self, *, not_found: bool = False):
        self._path = FakePathError(not_found=not_found)

    def is_path(self) -> bool:
        return True

    def get_path(self):
        return self._path


class FakeUploadReason:
    def __init__(self, *, conflict: bool = False):
        self._conflict = conflict

    def is_conflict(self) -> bool:
        return self._conflict


class FakeUploadPath:
    def __init__(self, *, conflict: bool = False):
        self.reason = FakeUploadReason(conflict=conflict)


class FakeUploadError:
    def __init__(self, *, conflict: bool = False):
        self._path = FakeUploadPath(conflict=conflict)

    def is_path(self) -> bool:
        return True

    def get_path(self):
        return self._path


class FakeApiError(Exception):
    def __init__(self, error):
        super().__init__("api error")
        self.error = error


class FakeAuthError(Exception):
    pass


class FakeDropbox:
    def __init__(self):
        self._meta_exists = set()
        self.uploaded = {}

    def files_get_metadata(self, path: str):
        if path in self._meta_exists:
            return {"path": path}
        raise FakeApiError(FakeMetaError(not_found=True))

    def files_upload(self, data: bytes, path: str, mode=None, autorename=None, mute=None):
        # simulate conflict if already uploaded/exists
        if path in self._meta_exists:
            raise FakeApiError(FakeUploadError(conflict=True))
        self._meta_exists.add(path)
        self.uploaded[path] = data
        return {"path": path}


def test_exists_true_when_metadata_found(monkeypatch):
    monkeypatch.setattr(dbc, "ApiError", FakeApiError)
    monkeypatch.setattr(dbc, "AuthError", FakeAuthError)

    dbx = FakeDropbox()
    dbx._meta_exists.add("/Reports/20260217.pdf")

    client = dbc.DropboxClient("x", dbx=dbx)
    assert client.exists("/Reports/20260217.pdf") is True


def test_exists_false_when_not_found(monkeypatch):
    monkeypatch.setattr(dbc, "ApiError", FakeApiError)
    monkeypatch.setattr(dbc, "AuthError", FakeAuthError)

    client = dbc.DropboxClient("x", dbx=FakeDropbox())
    assert client.exists("/Reports/missing.pdf") is False


def test_upload_new_success(monkeypatch):
    monkeypatch.setattr(dbc, "ApiError", FakeApiError)
    monkeypatch.setattr(dbc, "AuthError", FakeAuthError)

    dbx = FakeDropbox()
    client = dbc.DropboxClient("x", dbx=dbx)

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "file.pdf"
        p.write_bytes(b"%PDF-1.7 test")
        client.upload_new(p, "/Reports/20260217.pdf")

    assert "/Reports/20260217.pdf" in dbx.uploaded


def test_upload_new_conflict_raises(monkeypatch):
    monkeypatch.setattr(dbc, "ApiError", FakeApiError)
    monkeypatch.setattr(dbc, "AuthError", FakeAuthError)

    dbx = FakeDropbox()
    dbx._meta_exists.add("/Reports/20260217.pdf")
    client = dbc.DropboxClient("x", dbx=dbx)

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "file.pdf"
        p.write_bytes(b"%PDF-1.7 test")
        with pytest.raises(dbc.DropboxUploadConflict):
            client.upload_new(p, "/Reports/20260217.pdf")


def test_normalize_path_adds_leading_slash():
    assert dbc._normalize_dbx_path("Reports/20260217.pdf") == "/Reports/20260217.pdf"
