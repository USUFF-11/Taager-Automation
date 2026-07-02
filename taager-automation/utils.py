from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List


def calculate_selling_price(taager_price: Any, markup_percent: float) -> float:
    """Calculate the selling price using the configured markup percentage."""
    if taager_price is None:
        return 0.0

    taager_value = Decimal(str(taager_price))
    markup_value = Decimal(str(markup_percent)) / Decimal("100")
    selling_value = taager_value * (Decimal("1") + markup_value)
    return float(selling_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_product_row(product: Dict[str, Any], markup_percent: float) -> List[Any]:
    """Convert an API product payload into the Google Sheets row format."""
    financials = product.get("financials") or {}
    taager_price = financials.get("price")
    original_price = financials.get("originalPrice")
    profit = financials.get("profit")

    return [
        product.get("productId"),
        product.get("variantId"),
        product.get("sku"),
        product.get("name"),
        original_price,
        taager_price,
        calculate_selling_price(taager_price, markup_percent),
        markup_percent,
        profit,
        product.get("thumbnail"),
        product.get("createdAt"),
    ]


def format_execution_time(seconds: float) -> str:
    """Format elapsed seconds into a human-readable string."""
    return f"{seconds:.2f}s"


def utc_now_iso() -> str:
    """Return the current UTC timestamp as ISO 8601."""
    return datetime.now(timezone.utc).isoformat()
