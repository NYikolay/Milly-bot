from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import Settings


def create_storage(settings: Settings) -> RedisStorage:
    """
    Create the Redis-backed FSM storage.

    Purpose:
        Builds ``RedisStorage`` from the configured Redis DSN for persisting FSM
        state and data.

    Args:
        settings: Application settings holding the Redis DSN.

    Returns:
        RedisStorage: Storage instance bound to the configured Redis URL.

    Notes:
        - ``RedisStorage.from_url`` creates the Redis client lazily; no
          connection is opened in this function.
    """
    return RedisStorage.from_url(settings.redis_dsn)
