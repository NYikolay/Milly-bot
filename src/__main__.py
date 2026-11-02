from __future__ import annotations

import asyncio

import structlog

from src.core.bot import create_bot
from src.core.config import Environment, Settings
from src.core.dispatcher import create_dispatcher
from src.core.logging import setup_logging

logger = structlog.get_logger(__name__)


async def run_polling(settings: Settings) -> None:
    """
    Run the bot with long polling.

    Purpose:
        Creates the bot and dispatcher, processes updates through long polling,
        and closes the bot session when polling finishes.

    Args:
        settings: Application settings used to build the bot and dispatcher.

    Notes:
        - The startup lifetime hook removes any webhook before polling starts.
        - The bot session is closed in a ``finally`` block, so it is released
          even if polling raises.
    """
    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings)

    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
            close_bot_session=False,
        )
    finally:
        await bot.session.close()


def main() -> None:
    """
    Start the bot in the mode selected by the environment.

    Purpose:
        Loads settings, configures logging, and runs either the webhook server
        in production or long polling otherwise.

    Notes:
        - No arguments and no return value; settings come from the environment
          and ``.env``. Configuration validation errors propagate.
    """
    settings = Settings()
    setup_logging(settings.log_level, settings.resolved_log_format)

    if settings.environment is Environment.PRODUCTION:
        from src.core.webhook import run_webhook

        logger.info("bot_starting", mode="webhook")
        run_webhook(settings)
    else:
        logger.info("bot_starting", mode="polling")
        asyncio.run(run_polling(settings))


if __name__ == "__main__":
    main()
