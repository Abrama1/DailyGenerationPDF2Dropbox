from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Environment-driven settings.

    Supports BOTH Dropbox auth modes:
    1) Preferred (long-term): refresh token flow
       - DROPBOX_APP_KEY
       - DROPBOX_APP_SECRET
       - DROPBOX_REFRESH_TOKEN
    2) Fallback (legacy / local quick test): short-lived access token
       - DROPBOX_ACCESS_TOKEN
    """

    # Fixed source URL for the PDF (required)
    source_pdf_url: str = Field(..., alias="SOURCE_PDF_URL")

    # Dropbox auth (preferred)
    dropbox_app_key: str | None = Field(default=None, alias="DROPBOX_APP_KEY")
    dropbox_app_secret: str | None = Field(default=None, alias="DROPBOX_APP_SECRET")
    dropbox_refresh_token: str | None = Field(default=None, alias="DROPBOX_REFRESH_TOKEN")

    # Dropbox auth (optional fallback)
    dropbox_access_token: str | None = Field(default=None, alias="DROPBOX_ACCESS_TOKEN")

    # Existing Dropbox folder where PDFs will be appended
    # Example: "/Reports"
    dropbox_target_folder: str = Field("/Reports", alias="DROPBOX_TARGET_FOLDER")

    # SQLite DB file path
    db_path: str = Field("data/app.sqlite", alias="DB_PATH")

    # Optional admin token (only if we later add a manual trigger endpoint)
    admin_token: str | None = Field(default=None, alias="ADMIN_TOKEN")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def validate_dropbox_auth(self) -> "Settings":
        """
        Require either:
          - refresh-token auth (recommended), OR
          - access token (fallback)
        """
        has_refresh_auth = bool(
            self.dropbox_app_key and self.dropbox_app_secret and self.dropbox_refresh_token
        )
        has_access_token = bool(self.dropbox_access_token)

        if not (has_refresh_auth or has_access_token):
            raise ValueError(
                "Dropbox credentials are not configured. Provide either "
                "(DROPBOX_APP_KEY + DROPBOX_APP_SECRET + DROPBOX_REFRESH_TOKEN) "
                "or DROPBOX_ACCESS_TOKEN."
            )

        return self

    @property
    def has_dropbox_refresh_auth(self) -> bool:
        return bool(
            self.dropbox_app_key and self.dropbox_app_secret and self.dropbox_refresh_token
        )

    def dropbox_pdf_path(self, date_key: str) -> str:
        """
        Builds the Dropbox destination path for a date key, e.g.:
        date_key=20260217 -> /Reports/20260217.pdf
        """
        folder = self.dropbox_target_folder.rstrip("/")
        return f"{folder}/{date_key}.pdf"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()