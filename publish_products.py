from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from config import get_settings
from orders import GoogleSheetsError, OrderService

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Publish exactly one unpublished product to the Telegram channel and stop."""
    settings = get_settings()
    order_service = OrderService(settings)

    try:
        product = order_service.get_next_unpublished_product()
        if product is None:
            logger.info("No unpublished products found")
            return

        product_id = product.get("Product ID", "")
        name = product.get("Name", "")
        price = product.get("Selling Price", "")
        image = product.get("Image", "")

        if not product_id:
            logger.warning("Found a product without a Product ID; skipping")
            return

        caption = f"📦 {name}\n\n💰 السعر: {price}"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🛒 اطلب الآن", url=f"https://t.me/taager_products_bot?start={product_id}")]]
        )

        from telegram import Bot

        bot = Bot(settings.bot_token)
        bot.send_photo(
            chat_id=settings.channel_id,
            photo=image,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        order_service.mark_product_published(product_id)
        logger.info("Published product %s", product_id)
    except (GoogleSheetsError, TelegramError, Exception) as exc:
        logger.exception("Failed to publish product: %s", exc)


if __name__ == "__main__":
    main()
