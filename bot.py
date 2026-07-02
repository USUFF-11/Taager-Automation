from __future__ import annotations

import logging

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

    logger.info("Starting Telegram bot")
    app = Application.builder().token(settings.bot_token).build()

    # The conversation handler owns /start. Keeping a separate top-level /start handler
    # caused the command to be processed by two different paths and made the state flow
    # harder to reason about. Using only the conversation entry point avoids that conflict.
    app.add_handler(build_conversation_handler())
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()