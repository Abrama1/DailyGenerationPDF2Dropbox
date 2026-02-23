from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode

from app.config import Settings


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


def _build_real_dropbox_client(auth: Settings | str) -> dropbox.Dropbox:
    """
    Build a real Dropbox SDK client from either:
    - Settings (preferred)
    - raw access token string (legacy fallback / backward compatibility)
    """
    # Backward compatibility: allow old call style DropboxClient(access_token)
    if isinstance(auth, str):
        token = auth.strip()
        if not token:
            raise DropboxAuthFailed("Dropbox access token is empty.")
        return dropbox.Dropbox(oauth2_access_token=token, timeout=100)

    # Preferred: refresh-token flow (long-lived automation)
    if auth.has_dropbox_refresh_auth:
        return dropbox.Dropbox(
            oauth2_refresh_token=auth.dropbox_refresh_token,
            app_key=auth.dropbox_app_key,
            app_secret=auth.dropbox_app_secret,
            timeout=100,
        )

    # Fallback: short-lived access token
    if auth.dropbox_access_token:
        return dropbox.Dropbox(
            oauth2_access_token=auth.dropbox_access_token,
            timeout=100,
        )

    raise DropboxAuthFailed(
        "Dropbox credentials are not configured correctly. "
        "Provide refresh-token auth or access token."
    )


class DropboxClient:
    def __init__(
        self,
        auth: Settings | str | None = None,
        *,
        dbx: object | None = None,
    ) -> None:
        """
        `dbx` injection is for tests. In production pass:
          - Settings (recommended), or
          - access token string (legacy)
        """
        if dbx is not None:
            self._dbx = dbx
            return

        if auth is None:
            raise DropboxAuthFailed("Dropbox client requires Settings or access token.")

        self._dbx = _build_real_dropbox_client(auth)

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