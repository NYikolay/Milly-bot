from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Update logging middleware that binds context and records handler outcomes."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Log the processing of a Telegram update.

        Purpose:
            Binds structlog contextvars for updates, measures handler duration, and
            emits ``update_processed`` or ``update_failed`` log entries.

        Args:
            handler: Next middleware or handler in the chain.
            event: Incoming Telegram object.
            data: Middleware data passed to the handler.

        Returns:
            Any: The result returned by the wrapped handler.

        Raises:
            Exception: Any exception raised by the wrapped handler is logged and
                re-raised.

        Notes:
            - Non-``Update`` events bypass logging and are passed through unchanged.
            - Binds ``update_id``, ``update_type``, ``user_id``, and ``chat_id``.
            - Contextvars are cleared both before binding and in a ``finally`` block.
        """
        if not isinstance(event, Update):
            return await handler(event, data)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            update_id=event.update_id,
            update_type=event.event_type,
            user_id=_user_id(event),
            chat_id=_chat_id(event),
        )

        started_at = time.perf_counter()
        try:
            result = await handler(event, data)
        except Exception:
            logger.exception("update_failed", duration_ms=_elapsed_ms(started_at))
            raise
        else:
            logger.info("update_processed", duration_ms=_elapsed_ms(started_at))
            return result
        finally:
            structlog.contextvars.clear_contextvars()


def _user_id(update: Update) -> int | None:
    """
    Extract the user ID from an update.

    Purpose:
        Provides the ``user_id`` value for structlog context binding.

    Args:
        update: Telegram update to inspect.

    Returns:
        int | None: ID of the event's ``from_user``, or ``None`` if absent.
    """
    user = getattr(update.event, "from_user", None)
    return user.id if user is not None else None


def _chat_id(update: Update) -> int | None:
    """
    Extract the chat ID from an update.

    Purpose:
        Provides the ``chat_id`` value for structlog context binding.

    Args:
        update: Telegram update to inspect.

    Returns:
        int | None: ID of the event's chat, its nested message chat, or ``None``
            if absent.
    """
    chat = getattr(update.event, "chat", None)
    if chat is None:
        message = getattr(update.event, "message", None)
        chat = getattr(message, "chat", None)
    return chat.id if chat is not None else None


def _elapsed_ms(started_at: float) -> float:
    """
    Calculate elapsed time in milliseconds.

    Purpose:
        Produces the ``duration_ms`` value for update logging.

    Args:
        started_at: Start timestamp from ``time.perf_counter()``.

    Returns:
        float: Elapsed milliseconds rounded to 2 decimal places.
    """
    return round((time.perf_counter() - started_at) * 1000, 2)
