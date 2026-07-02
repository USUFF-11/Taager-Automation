from __future__ import annotations

import logging
import time

import requests
from telegram._update import Update
from telegram.ext import Application, ContextTypes

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

    requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates?offset=-1&timeout=1",
        timeout=5,
    )
    time.sleep(3)

    logger.info("Starting Telegram bot")

    app = Application.builder().token(token).build()
    app.add_handler(build_conversation_handler())
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()