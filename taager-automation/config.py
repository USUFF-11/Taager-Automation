from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Application configuration loaded from environment and .env."""

    def __init__(self) -> None:
        self.base_dir = BASE_DIR
        self.bearer_token = os.getenv("TAAGER_BEARER_TOKEN", "").strip()
        self.google_credentials_path = os.getenv(
            "GOOGLE_CREDENTIALS_PATH", str(BASE_DIR / "credentials.json")
        ).strip()
        self.spreadsheet_name = os.getenv("GOOGLE_SPREADSHEET_NAME", "Taager Automation").strip()
        self.worksheet_name = os.getenv("GOOGLE_WORKSHEET_NAME", "Products").strip()
        self.markup_percent = float(os.getenv("DEFAULT_MARKUP_PERCENT", "20"))
        self.api_base_url = os.getenv(
            "TAAGER_API_BASE_URL",
            "https://merchant.api.taager.com/api/products/variants",
        ).strip()
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.page_size = int(os.getenv("PAGE_SIZE", "100"))
        self.sort_by = os.getenv("SORT_BY", "introducedAt").strip()
        self.sort_order = os.getenv("SORT_ORDER", "descending").strip()
        self.required_columns: List[str] = [
            "Product ID",
            "Variant ID",
            "SKU",
            "Name",
            "Original Price",
            "Taager Price",
            "Selling Price",
            "Markup %",
            "Profit",
            "Image",
            "Created At",
        ]
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]


def get_settings() -> Settings:
    """Return a configured settings instance."""
    return Settings()


def validate_settings(settings: Settings) -> None:
    """Validate configuration before running the synchronization."""
    if not settings.bearer_token:
        raise ValueError("TAAGER_BEARER_TOKEN is missing. Set it in the .env file.")

    credentials_path = Path(settings.google_credentials_path)
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google credentials file was not found: {credentials_path}"
        )
