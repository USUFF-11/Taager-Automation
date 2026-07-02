from __future__ import annotations

from typing import Dict, List, Tuple

import gspread
from google.oauth2.service_account import Credentials

from config import Settings
from utils import build_product_row


class GoogleSheetsError(Exception):
    """Raised when Google Sheets operations fail."""


class GoogleSheetService:
    """Service that synchronizes product data into a Google Sheet."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = None
        self.worksheet = None
        self.existing_product_rows: Dict[str, int] = {}

    def connect(self) -> None:
        """Connect to Google Sheets using service account credentials."""
        if self.worksheet is not None:
            return

        try:
            credentials = Credentials.from_service_account_file(
                self.settings.google_credentials_path,
                scopes=self.settings.scopes,
            )
            self.client = gspread.authorize(credentials)
            self.worksheet = self.client.open(self.settings.spreadsheet_name).worksheet(
                self.settings.worksheet_name
            )
            self._ensure_headers()
            self._load_existing_products()
        except Exception as exc:  # pragma: no cover - defensive logging path
            raise GoogleSheetsError(f"Unable to connect to Google Sheets: {exc}") from exc

    def upsert_products(self, products: List[Dict[str, object]], markup_percent: float) -> Tuple[int, int]:
        """Insert new products and update existing products based on Product ID."""
        self.connect()

        rows_to_append: List[List[object]] = []
        rows_to_update: List[Tuple[int, List[object]]] = []
        seen_product_ids: set[str] = set()

        for product in products:
            product_id = str(product.get("productId") or "").strip()
            if not product_id or product_id in seen_product_ids:
                continue

            seen_product_ids.add(product_id)
            row = build_product_row(product, markup_percent)

            if product_id in self.existing_product_rows:
                row_number = self.existing_product_rows[product_id]
                rows_to_update.append((row_number, row))
            else:
                rows_to_append.append(row)

        try:
            if rows_to_update:
                update_requests = [
                    {
                        "range": f"A{row_number}:K{row_number}",
                        "values": [row],
                    }
                    for row_number, row in rows_to_update
                ]
                self.worksheet.batch_update(update_requests, value_input_option="RAW")

            if rows_to_append:
                self.worksheet.append_rows(rows_to_append, value_input_option="RAW")
        except Exception as exc:
            raise GoogleSheetsError(f"Unable to write to Google Sheets: {exc}") from exc

        return len(rows_to_append), len(rows_to_update)

    def _ensure_headers(self) -> None:
        """Ensure the worksheet begins with the exact required column headers."""
        try:
            values = self.worksheet.get_all_values()
            if not values or values[0] != self.settings.required_columns:
                self.worksheet.batch_update(
                    [
                        {
                            "range": "A1:K1",
                            "values": [self.settings.required_columns],
                        }
                    ],
                    value_input_option="RAW",
                )
        except Exception as exc:
            raise GoogleSheetsError(f"Unable to prepare worksheet headers: {exc}") from exc

    def _load_existing_products(self) -> None:
        """Create a lookup of Product ID to worksheet row number."""
        try:
            values = self.worksheet.get_all_values()
            self.existing_product_rows = {}

            for row_number, row in enumerate(values[1:], start=2):
                if row and row[0]:
                    self.existing_product_rows[str(row[0])] = row_number
        except Exception as exc:
            raise GoogleSheetsError(f"Unable to read existing rows from Google Sheets: {exc}") from exc
