from __future__ import annotations

from typing import Any, Dict, List

import requests

from config import Settings


class TaagerAPIError(Exception):
    """Raised when the Taager API request fails."""


class TaagerAPIClient:
    """Client for fetching products from the Taager API with retries."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()

    def fetch_all_products(self) -> List[Dict[str, Any]]:
        """Fetch all products from the Taager API using pagination."""
        all_products: List[Dict[str, Any]] = []
        page = 1

        while True:
            payload = self._get_products_page(page)
            if not payload:
                break

            all_products.extend(payload)
            page += 1

        return all_products

    def _get_products_page(self, page: int) -> List[Dict[str, Any]]:
        """Request one page of products and return the parsed product list."""
        params = {
            "page": page,
            "pageSize": self.settings.page_size,
            "sortBy": self.settings.sort_by,
            "sortOrder": self.settings.sort_order,
        }

        headers = {
            "Authorization": f"Bearer {self.settings.bearer_token}",
            "country": "EGY",
            "platform": "web",
            "accept": "application/json",
        }

        for attempt in range(1, self.settings.max_retries + 1):
            try:
                response = self.session.get(
                    self.settings.api_base_url,
                    headers=headers,
                    params=params,
                    timeout=self.settings.request_timeout,
                )
                if response.status_code == 200:
                    return self._extract_products(response.json())

                if response.status_code in {408, 429} or response.status_code >= 500:
                    if attempt < self.settings.max_retries:
                        continue

                raise TaagerAPIError(
                    f"Taager API request failed with status {response.status_code}: {response.text}"
                )
            except requests.RequestException as exc:
                if attempt < self.settings.max_retries:
                    continue
                raise TaagerAPIError(f"Taager API request failed: {exc}") from exc

        return []

    @staticmethod
    def _extract_products(payload: Any) -> List[Dict[str, Any]]:
        """Normalize the API response into a list of product dictionaries."""
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            for key in ("data", "products", "items", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]

        return []
