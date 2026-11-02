from collections.abc import Callable

from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import Settings
from src.core.dispatcher import create_dispatcher


def test_dispatcher_uses_redis_storage(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings()

    dispatcher = create_dispatcher(settings)

    assert isinstance(dispatcher.storage, RedisStorage)
