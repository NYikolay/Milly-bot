from __future__ import annotations

import structlog
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from src.core.bot import create_bot
from src.core.config import Settings
from src.core.dispatcher import create_dispatcher
from src.core.logging import setup_logging

logger = structlog.get_logger(__name__)


async def healthcheck(_request: web.Request) -> web.Response:
    """
    Report service health.

    Purpose:
        Responds to health probes with a fixed ``ok`` body and HTTP ``200``.

    Args:
        _request: Incoming HTTP request; unused.

    Returns:
        web.Response: Plain-text response with status ``200`` and body ``ok``.
    """
    return web.Response(text="ok")


def create_web_app(
    bot: Bot, dispatcher: Dispatcher, settings: Settings
) -> web.Application:
    """
    Build the aiohttp application serving the webhook.

    Purpose:
        Registers the ``/health`` endpoint and the webhook route, wiring the
        bot and dispatcher into aiogram's request handler.

    Args:
        bot: Bot used to process incoming updates.
        dispatcher: Dispatcher that routes the updates.
        settings: Application settings with the webhook path and secret.

    Returns:
        web.Application: Configured aiohttp application.

    Notes:
        - ``setup_application()`` must run before
          ``SimpleRequestHandler.register()`` so shutdown hooks are ordered
          correctly.
        - Updates are handled synchronously in the request
          (``handle_in_background=False``).
    """
    app = web.Application()
    app.router.add_get("/health", healthcheck)

    setup_application(app, dispatcher, bot=bot)
    webhook_handler = SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.webhook_secret_value,
        handle_in_background=False,
    )
    webhook_handler.register(app, path=settings.webhook_path)
    return app


def run_webhook(settings: Settings) -> None:
    """
    Run the bot in webhook mode.

    Purpose:
        Configures logging, validates the webhook URL, creates the bot and
        dispatcher, builds the aiohttp application, and starts the blocking
        webhook server.

    Args:
        settings: Application settings with the webhook URL, bind address, and
            port.

    Raises:
        RuntimeError: If no webhook URL is configured.

    Notes:
        - Uses ``web.run_app``, which blocks until the server stops. The
          startup hook registers the webhook with Telegram.
    """
    setup_logging(settings.log_level, settings.resolved_log_format)

    webhook_url = settings.webhook_url
    if webhook_url is None:
        raise RuntimeError("WEBHOOK_BASE_URL is required in production")

    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings)

    app = create_web_app(bot=bot, dispatcher=dispatcher, settings=settings)
    logger.info(
        "webhook_server_starting",
        host=settings.webhook_host,
        port=settings.webhook_port,
        url=webhook_url,
    )
    web.run_app(
        app,
        host=settings.webhook_host,
        port=settings.webhook_port,
        print=None,
    )
