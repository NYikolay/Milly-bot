from functools import partial

import structlog
from aiogram import Bot, Dispatcher

from src.core.config import Environment, Settings

logger = structlog.get_logger(__name__)


async def on_startup(bot: Bot, dispatcher: Dispatcher, settings: Settings) -> None:
    """
    Run startup actions for the current environment.

    Purpose:
        In production, registers the webhook with its URL, secret, pending-update
        policy, and the update types used by the dispatcher. In local mode,
        removes any existing webhook.

    Args:
        bot: Bot whose webhook is configured or removed.
        dispatcher: Dispatcher used to resolve the allowed update types.
        settings: Application settings with the environment and webhook options.

    Raises:
        RuntimeError: If the environment is production and no webhook URL is
            configured.
    """
    if settings.environment is Environment.PRODUCTION:
        webhook_url = settings.webhook_url
        if webhook_url is None:
            raise RuntimeError("WEBHOOK_BASE_URL is required in production")

        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.webhook_secret_value,
            drop_pending_updates=settings.drop_pending_updates,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        logger.info("webhook_set", url=webhook_url)
    else:
        await bot.delete_webhook(drop_pending_updates=settings.drop_pending_updates)
        logger.info("webhook_removed")


async def on_shutdown(bot: Bot, settings: Settings) -> None:
    """
    Run shutdown actions for the current environment.

    Purpose:
        In production, deletes the registered webhook. In local mode, does
        nothing because long polling leaves no webhook to remove.

    Args:
        bot: Bot whose webhook is deleted.
        settings: Application settings with the current environment.

    Notes:
        - Redis storage is intentionally not closed here; the dispatcher handles
          it automatically during shutdown.
    """
    if settings.environment is Environment.PRODUCTION:
        await bot.delete_webhook()
        logger.info("webhook_deleted")


def register_lifetime(dispatcher: Dispatcher, settings: Settings) -> None:
    """
    Register startup and shutdown handlers on the dispatcher.

    Purpose:
        Binds ``settings`` into the lifetime handlers via ``functools.partial``
        and attaches them to the dispatcher's startup and shutdown signals.

    Args:
        dispatcher: Dispatcher that will process updates and emit lifecycle
            signals.
        settings: Application settings passed to the lifetime handlers.

    Notes:
        - Register the hooks on the same dispatcher that processes updates.
    """
    dispatcher.startup.register(partial(on_startup, settings=settings))
    dispatcher.shutdown.register(partial(on_shutdown, settings=settings))
