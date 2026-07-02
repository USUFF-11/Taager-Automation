from __future__ import annotations

import logging
import time

from config import get_settings, validate_settings
from countries import get_country_config
from google_sheet import GoogleSheetService, GoogleSheetsError
from taager_api import TaagerAPIClient, TaagerAPIError
from utils import format_execution_time

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SYNC_INTERVAL = 60 * 60  # 60 minutes


def sync_once(settings, country_config) -> None:
    start_time = time.perf_counter()
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
        logger.info(
            "[%s] Added=%d Updated=%d Time=%s",
            country_code, products_added, products_updated, elapsed,
        )
    except (TaagerAPIError, GoogleSheetsError, ValueError, FileNotFoundError) as exc:
        logger.exception("[%s] Sync failed: %s", country_code, exc)


def main() -> None:
    """Run the Taager to Google Sheets synchronization process continuously."""
    settings = get_settings()
    validate_settings(settings)

    country_config = get_country_config()
    country_code = country_config.code

    logger.info("Starting sync loop for %s (every %d seconds)", country_code, SYNC_INTERVAL)

    while True:
        sync_once(settings, country_config)
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
