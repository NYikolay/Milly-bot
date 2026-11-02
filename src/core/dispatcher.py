from aiogram import Dispatcher

from src.core.config import Settings
from src.core.lifetime import register_lifetime
from src.core.storage import create_storage
from src.handlers import router as root_router
from src.middlewares.logging import LoggingMiddleware


def create_dispatcher(settings: Settings) -> Dispatcher:
    """
    Create and configure the aiogram dispatcher.

    Purpose:
        Builds a ``Dispatcher`` backed by Redis storage, attaches the logging
        middleware, includes the root router, and registers lifetime hooks.

    Args:
        settings: Application settings used for storage and lifetime handlers.

    Returns:
        Dispatcher: Dispatcher ready to process updates.

    Notes:
        - aiogram's ``Dispatcher`` registers ``fsm.close`` on shutdown, so the
          Redis storage is closed automatically; do not close it separately.
    """
    dispatcher = Dispatcher(storage=create_storage(settings))
    dispatcher.update.outer_middleware(LoggingMiddleware())
    dispatcher.include_router(root_router)
    register_lifetime(dispatcher, settings)
    return dispatcher
