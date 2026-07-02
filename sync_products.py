from __future__ import annotations

import time

from config import get_settings, validate_settings
from countries import get_country_config
from google_sheet import GoogleSheetService, GoogleSheetsError
from taager_api import TaagerAPIClient, TaagerAPIError
from utils import format_execution_time


def main() -> None:
    """Run the Taager to Google Sheets synchronization process."""
    start_time = time.perf_counter()
    settings = get_settings()
    validate_settings(settings)

    country_config = get_country_config()
    country_code = country_config.code

    try:
        taager_client = TaagerAPIClient(settings, country_code=country_code)
        google_sheet_service = GoogleSheetService(settings, sheet_name=country_config.products_sheet)

        products = taager_client.fetch_all_products()
        products_added, products_updated = google_sheet_service.upsert_products(
            products,
            settings.markup_percent,
        )

        elapsed = format_execution_time(time.perf_counter() - start_time)
        print(f"[{country_code}] Products Added: {products_added}")
        print(f"[{country_code}] Products Updated: {products_updated}")
        print(f"[{country_code}] Execution Time: {elapsed}")
    except (TaagerAPIError, GoogleSheetsError, ValueError, FileNotFoundError) as exc:
        print(f"[{country_code}] Synchronization failed: {exc}")
        raise


if __name__ == "__main__":
    main()
