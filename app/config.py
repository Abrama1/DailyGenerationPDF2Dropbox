# app/config.py
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Environment-driven settings.

    We keep this strict: if a required value is missing, the app should fail fast.
    """

    # Fixed source URL for the PDF (required)
    source_pdf_url: str = Field(..., alias="SOURCE_PDF_URL")

    # Dropbox API token (required)
    dropbox_access_token: str = Field(..., alias="DROPBOX_ACCESS_TOKEN")

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
