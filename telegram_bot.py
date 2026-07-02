from __future__ import annotations

import asyncio
import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from config import get_settings, validate_settings
from countries import get_country_config
from orders import GoogleSheetsError, OrderService

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CHECK_INTERVAL = 5 * 60  # 5 minutes


async def publish_next_product(
    bot: Bot, order_service: OrderService, channel_id: str, country_config
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

    deep_link_suffix = f"SAU_{product_id}" if country_config.code != "EG" else product_id
    deep_link = f"https://t.me/{country_config.bot_username}?start={deep_link_suffix}"
    logger.info("Generated deep link: %s", deep_link)

    caption = f"""🛍 {name}

💰 السعر: {price} {country_config.currency_symbol}

{country_config.shipping_text}

<a href="{deep_link}">🛒 اطلب الآن</a>"""
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🛒 اطلب الآن",
                    url=deep_link,
                )
            ]
        ]
    )

    try:
        await bot.send_photo(
            chat_id=channel_id,
            photo=image,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.warning("Photo failed for product %s, trying text-only: %s", product_id, e)
        try:
            await bot.send_message(
                chat_id=channel_id,
                text=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e2:
            logger.warning("Text-only also failed for product %s: %s", product_id, e2)
            return False

    logger.info("Message sent for product %s", product_id)
    order_service.mark_product_published(product_id)
    logger.info("Published At updated for product %s", product_id)
    return True


async def main() -> None:
    settings = get_settings()
    validate_settings(settings)

    country_config = get_country_config()
    country_code = country_config.code
    logger.info("Starting publisher for country: %s", country_code)

    order_service = OrderService(settings, country_code=country_code)
    bot = Bot(settings.bot_token)

    logger.info(
        "Starting publisher loop (checking every %d seconds)",
        CHECK_INTERVAL,
    )

    while True:
        try:
            await publish_next_product(bot, order_service, country_config.channel_id, country_config)
        except TelegramError:
            logger.exception("Telegram error during publish")
        except GoogleSheetsError:
            logger.exception("Google Sheets error during publish")
        except Exception:
            logger.exception("Unexpected error during publish")

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())