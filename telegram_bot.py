from __future__ import annotations

import asyncio
import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from config import get_settings, validate_settings
from orders import GoogleSheetsError, OrderService

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CHECK_INTERVAL = 5 * 60  # 5 minutes


async def publish_next_product(
    bot: Bot, order_service: OrderService, channel_id: str
) -> bool:
    product = order_service.get_next_unpublished_product()

    if product is None:
        logger.info("No unpublished products found")
        return False

    product_id = str(product.get("Product ID", "")).strip()
    name = str(product.get("Name", "")).strip()
    price = str(product.get("Selling Price", "")).strip()
    image = str(product.get("Image", "")).strip()

    if not product_id:
        logger.warning("Found a product without a Product ID; skipping")
        return False

    logger.info("Publishing product: %s", product_id)

    caption = f"""🛍 {name}

💰 السعر: {price} جنيه

🚚 الشحن يحسب حسب المحافظة"""
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🛒 اطلب الآن",
                    url=f"https://t.me/taager_products_bot?start={product_id}",
                )
            ]
        ]
    )

    await bot.send_photo(
        chat_id=channel_id,
        photo=image,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    logger.info("Message sent for product %s", product_id)
    order_service.mark_product_published(product_id)
    logger.info("Published At updated for product %s", product_id)
    return True


async def main() -> None:
    settings = get_settings()
    validate_settings(settings)

    order_service = OrderService(settings)
    bot = Bot(settings.bot_token)

    logger.info(
        "Starting publisher loop (checking every %d seconds)",
        CHECK_INTERVAL,
    )

    while True:
        try:
            await publish_next_product(bot, order_service, settings.channel_id)
        except TelegramError:
            logger.exception("Telegram error during publish")
        except GoogleSheetsError:
            logger.exception("Google Sheets error during publish")
        except Exception:
            logger.exception("Unexpected error during publish")

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())