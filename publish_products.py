from __future__ import annotations

import asyncio
import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from config import get_settings
from orders import GoogleSheetsError, OrderService

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    order_service = OrderService(settings)

    logger.info("Reading sheet")
    product = order_service.get_next_unpublished_product()

    if product is None:
        logger.info("No unpublished products found")
        return

    product_id = str(product.get("Product ID", "")).strip()
    name = str(product.get("Name", "")).strip()
    price = str(product.get("Selling Price", "")).strip()
    image = str(product.get("Image", "")).strip()

    if not product_id:
        logger.warning("Found a product without a Product ID; skipping")
        return

    logger.info("Product found: %s", product_id)

    caption = f"""📦 {name}\n\n💰 السعر: {price}
    🚚 الشحن يحسب حسب المحافظة
    📞 اطلب الآن من خلال الزر بالأسفل 👇"""
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

    bot = Bot(settings.bot_token)

    try:
        logger.info("Sending message for product %s", product_id)
        message = await bot.send_photo(
            chat_id=settings.channel_id,
            photo=image,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        logger.info(
            "Message sent: product=%s message_id=%s",
            product_id,
            getattr(message, "message_id", None),
        )

        logger.info("Updating Published At for product %s", product_id)
        order_service.mark_product_published(product_id)
        logger.info("Done")
    except TelegramError:
        logger.exception("Telegram exception while sending product %s", product_id)
        raise
    except GoogleSheetsError:
        logger.exception("Google Sheets exception for product %s", product_id)
        raise
    finally:
        try:
            await bot.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())