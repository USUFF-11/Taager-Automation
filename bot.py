from __future__ import annotations

import logging
import time

import requests
from telegram import Bot
from telegram._update import Update
from telegram.ext import Application, ContextTypes, Updater

from config import get_settings, validate_settings
from conversation import build_conversation_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    validate_settings(settings)

    token = settings.bot_token

    # Forcefully close any existing polling connection
    requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates?offset=-1&timeout=1",
        timeout=5,
    )
    time.sleep(3)

    logger.info("Starting Telegram bot")

    updater = Updater(token=token, update_queue=None)
    updater.dispatcher.add_handler(build_conversation_handler())
    updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
    logger.info("Bot is running")
    updater.idle()


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()