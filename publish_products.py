from __future__ import annotations

import asyncio
import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from config import get_settings
from countries import get_country_config
from orders import GoogleSheetsError, OrderService

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    country_config = get_country_config()
    country_code = country_config.code
    order_service = OrderService(settings, country_code=country_code)

    deep_link_suffix = f"{country_code}-" if country_code != "EG" else ""

    logger.info("Reading sheet for %s", country_code)
    product = order_service.get_next_unpublished_product()

    if product is None:
        logger.info("No unpublished products found for %s", country_code)
        return

    product_id = str(product.get("Product ID", "")).strip()
    name = str(product.get("Name", "")).strip()
    price = str(product.get("Selling Price", "")).strip()
    image = str(product.get("Image", "")).strip()

    if not product_id:
        logger.warning("Found a product without a Product ID; skipping")
        return

    logger.info("Product found for %s: %s", country_code, product_id)

    caption = f"""📦 {name}
💰 السعر: {price} {country_config.currency_symbol}
{country_config.shipping_text}
📞 اطلب الآن من خلال الزر بالأسفل 👇"""
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🛒 اطلب الآن",
                    url=f"tg://resolve?domain={country_config.bot_username}&start={deep_link_suffix}{product_id}",
                )
            ]
        ]
    )

    bot = Bot(settings.bot_token)

    try:
        logger.info("Sending message for product %s", product_id)
        message = await bot.send_photo(
            chat_id=country_config.channel_id,
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