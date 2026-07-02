from __future__ import annotations

import time
from typing import Optional

from config import get_settings, validate_settings
from google_sheet import GoogleSheetService, GoogleSheetsError
from taager_api import TaagerAPIClient, TaagerAPIError
from utils import format_execution_time


def main() -> None:
    """Run the Taager to Google Sheets synchronization process."""
    start_time = time.perf_counter()
    settings = get_settings()
    validate_settings(settings)

    try:
        taager_client = TaagerAPIClient(settings)
        google_sheet_service = GoogleSheetService(settings)

        products = taager_client.fetch_all_products()
        products_added, products_updated = google_sheet_service.upsert_products(
            products,
            settings.markup_percent,
        )

        elapsed = format_execution_time(time.perf_counter() - start_time)
        print(f"Products Added: {products_added}")
        print(f"Products Updated: {products_updated}")
        print(f"Execution Time: {elapsed}")
    except (TaagerAPIError, GoogleSheetsError, ValueError, FileNotFoundError) as exc:
        print(f"Synchronization failed: {exc}")
        raise


if __name__ == "__main__":
    main()
