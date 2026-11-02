import logging
from collections.abc import Callable

import pytest
import structlog

from src.core.config import Settings

_ENV_VARS = (
    "ENVIRONMENT",
    "BOT_TOKEN",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "WEBHOOK_BASE_URL",
    "WEBHOOK_PATH",
    "WEBHOOK_SECRET",
    "WEBHOOK_HOST",
    "WEBHOOK_PORT",
    "DROP_PENDING_UPDATES",
    "REDIS_URL",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def make_settings() -> Callable[..., Settings]:
    def factory(**overrides: object) -> Settings:
        return Settings(_env_file=None, bot_token="42:TEST", **overrides)

    return factory


@pytest.fixture
def restore_logging() -> None:
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
    structlog.reset_defaults()
