from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.core.config import Settings


def create_bot(settings: Settings) -> Bot:
    """
    Create the aiogram bot instance.

    Purpose:
        Builds a ``Bot`` from the configured token and applies HTML as the default
        parse mode for outgoing messages.

    Args:
        settings: Application settings holding the bot token.

    Returns:
        Bot: Configured aiogram bot with HTML parse mode.
    """
    return Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
