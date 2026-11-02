from contextlib import suppress

import structlog
from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

logger = structlog.get_logger(__name__)

router = Router(name="errors")


@router.errors()
async def handle_error(event: ErrorEvent) -> bool:
    """
    Handle exceptions raised while processing updates.

    Purpose:
        Logs handler failures and optionally notifies the user with an apology.

    Args:
        event: Error event containing the failed update and exception.

    Returns:
        bool: Always ``True`` to stop further error handling.

    Notes:
        - The failure is logged with exception info and ``update_id``.
        - The apology is sent only when the update contains a message.
        - ``TelegramAPIError`` raised while replying is suppressed.
    """
    logger.error(
        "update_handling_failed",
        exc_info=event.exception,
        update_id=event.update.update_id,
    )

    message = event.update.message
    if message is not None:
        with suppress(TelegramAPIError):
            await message.answer("Что-то пошло не так. Попробуй позже.")

    return True
