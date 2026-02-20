from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode


@dataclass(frozen=True)
class DropboxClientError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class DropboxAuthFailed(DropboxClientError):
    pass


@dataclass(frozen=True)
class DropboxUploadConflict(DropboxClientError):
    """
    Raised when attempting to upload a file but the destination already exists
    and autorename is disabled.
    """
    pass


def _normalize_dbx_path(path: str) -> str:
    """
    Ensures:
      - leading slash
      - no trailing slash for file paths
      - collapses accidental double slashes
    """
    p = (path or "").strip().replace("\\", "/")
    if not p.startswith("/"):
        p = "/" + p
    while "//" in p:
        p = p.replace("//", "/")
    return p


def _is_not_found_api_error(e: ApiError) -> bool:
    # Works for metadata lookup errors
    try:
        err = e.error
        if hasattr(err, "is_path") and err.is_path():
            p = err.get_path()
            return hasattr(p, "is_not_found") and p.is_not_found()
    except Exception:
        pass
    return False


def _is_upload_conflict_api_error(e: ApiError) -> bool:
    # Works for upload errors with mode=add and autorename=False
    try:
        err = e.error
        if hasattr(err, "is_path") and err.is_path():
            p = err.get_path()
            # UploadWriteFailed has `reason`, then `is_conflict`
            reason = getattr(p, "reason", None)
            if reason is not None and hasattr(reason, "is_conflict") and reason.is_conflict():
                return True
    except Exception:
        pass
    return False


class DropboxClient:
    def __init__(self, access_token: str, *, dbx: object | None = None) -> None:
        # `dbx` injection is for testing. In prod we create a real Dropbox client.
        self._dbx = dbx if dbx is not None else dropbox.Dropbox(access_token)

    def exists(self, path: str) -> bool:
        path = _normalize_dbx_path(path)
        try:
            self._dbx.files_get_metadata(path)  # type: ignore[attr-defined]
            return True
        except AuthError as e:
            raise DropboxAuthFailed(f"Dropbox auth failed: {e}") from e
        except ApiError as e:
            if _is_not_found_api_error(e):
                return False
            raise DropboxClientError(f"Dropbox API error (exists check): {e}") from e

    def upload_new(self, local_path: str | Path, dropbox_path: str) -> None:
        """
        Uploads a file to Dropbox in a way that NEVER auto-renames.
        - mode=add
        - autorename=False
        If the file already exists, raises DropboxUploadConflict.
        """
        dropbox_path = _normalize_dbx_path(dropbox_path)
        local_path = Path(local_path)

        try:
            data = local_path.read_bytes()
        except Exception as e:
            raise DropboxClientError(f"Failed to read local file for upload: {e}") from e

        try:
            # mode=add + autorename=False => conflict should error instead of creating " (1)"
            self._dbx.files_upload(  # type: ignore[attr-defined]
                data,
                dropbox_path,
                mode=WriteMode.add,
                autorename=False,
                mute=True,
            )
        except AuthError as e:
            raise DropboxAuthFailed(f"Dropbox auth failed: {e}") from e
        except ApiError as e:
            if _is_upload_conflict_api_error(e):
                raise DropboxUploadConflict(f"Dropbox file already exists: {dropbox_path}") from e
            raise DropboxClientError(f"Dropbox API error (upload): {e}") from e
