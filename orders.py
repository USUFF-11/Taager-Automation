from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

from config import Settings
from countries import get_country_config


class GoogleSheetsError(Exception):
    """Raised when Google Sheets operations fail."""


class OrderService:
    """Service responsible for reading product data and saving orders to Google Sheets."""

    def __init__(self, settings: Settings, country_code: str | None = None) -> None:
        self.settings = settings
        self.country_config = get_country_config(country_code)
        self.client = None
        self.workbook = None
        self.products_worksheet = None
        self.orders_worksheet = None

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Find a product in the Products sheet by Product ID."""
        worksheet = self._get_products_worksheet()
        records = worksheet.get_all_records()
        for row in records:
            if str(row.get("Product ID", "")).strip() == str(product_id).strip():
                return row
        return None

    def save_order(self, order_data: Dict[str, Any]) -> None:
        """Append a completed order to the Orders sheet."""
        worksheet = self._get_orders_worksheet()
        headers = self._get_order_headers()
        row = [order_data.get(header, "") for header in headers]
        worksheet.append_row(row, value_input_option="RAW")

    def get_next_unpublished_product(self) -> Optional[Dict[str, Any]]:
        """Return the first product row whose Published At cell is empty."""
        worksheet = self._get_products_worksheet()
        records = worksheet.get_all_records()
        for row in records:
            published_at = str(row.get("Published At", "") or "").strip()
            if not published_at:
                return row
        return None

    def mark_product_published(self, product_id: Any) -> None:
        """Write the current datetime into the Published At column for a product row."""
        worksheet = self._get_products_worksheet()
        records = worksheet.get_all_values()
        if not records:
            return

        headers = records[0]
        try:
            published_at_index = headers.index("Published At")
        except ValueError:
            raise GoogleSheetsError("Published At column not found in Products sheet")

        for row_index, row in enumerate(records[1:], start=2):
            product_id_value = row[0] if row else ""
            if str(product_id_value).strip() == str(product_id).strip():
                worksheet.update_cell(row_index, published_at_index + 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                return

    def _get_products_sheet_name(self) -> str:
        env_override = self.settings.worksheet_name
        if env_override:
            return env_override
        return self.country_config.products_sheet

    def _get_orders_sheet_name(self) -> str:
        env_override = self.settings.orders_worksheet_name
        if env_override:
            return env_override
        return self.country_config.orders_sheet

    def _get_products_worksheet(self):
        if self.products_worksheet is not None:
            return self.products_worksheet

        workbook = self._get_workbook()
        self.products_worksheet = workbook.worksheet(self._get_products_sheet_name())
        return self.products_worksheet

    def _get_orders_worksheet(self):
        if self.orders_worksheet is not None:
            return self.orders_worksheet

        workbook = self._get_workbook()
        sheet_name = self._get_orders_sheet_name()
        try:
            self.orders_worksheet = workbook.worksheet(sheet_name)
        except WorksheetNotFound:
            self.orders_worksheet = workbook.add_worksheet(
                title=sheet_name,
                rows=1000,
                cols=30,
            )

        self._ensure_headers(self.orders_worksheet, self._get_order_headers())
        return self.orders_worksheet

    def _get_workbook(self):
        if self.workbook is not None:
            return self.workbook

        try:
            creds_json = os.getenv("GOOGLE_CREDENTIALS")
            if creds_json:
                credentials = Credentials.from_service_account_info(
                    json.loads(creds_json),
                    scopes=self.settings.scopes,
                )
            else:
                credentials = Credentials.from_service_account_file(
                    self.settings.google_credentials_path,
                    scopes=self.settings.scopes,
                )
            self.client = gspread.authorize(credentials)
            self.workbook = self.client.open(self.settings.spreadsheet_name)
        except Exception as exc:  # pragma: no cover - defensive logging path
            raise GoogleSheetsError(f"Unable to connect to Google Sheets: {exc}") from exc

        return self.workbook

    @staticmethod
    def _ensure_headers(worksheet, headers: List[str]) -> None:
        values = worksheet.get_all_values()
        if not values or values[0] != headers:
            worksheet.update(
                f"A1:{OrderService._column_name(len(headers))}1",
                [headers],
                value_input_option="RAW",
            )

    @staticmethod
    def _column_name(index: int) -> str:
        result = ""
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            result = chr(65 + remainder) + result
        return result

    @staticmethod
    def _get_order_headers() -> List[str]:
        return [
            "Order ID",
            "Product ID",
            "Product Name",
            "Selling Price",
            "Quantity",
            "Customer Name",
            "Province",
            "Address",
            "Phone",
            "Phone2",
            "Notes",
            "Facebook Page",
            "Facebook Link",
            "Country",
            "Color",
            "Size",
            "Order Time",
            "Status",
        ]
