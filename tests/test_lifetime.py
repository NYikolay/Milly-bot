import asyncio
from collections.abc import Callable
from typing import Any

from src.core.config import Environment, Settings
from src.core.lifetime import on_shutdown, on_startup


class FakeBot:
    def __init__(self) -> None:
        self.set_webhook_calls: list[dict[str, Any]] = []
        self.delete_webhook_calls: list[dict[str, Any]] = []

    async def set_webhook(self, **kwargs: Any) -> bool:
        self.set_webhook_calls.append(kwargs)
        return True

    async def delete_webhook(self, **kwargs: Any) -> bool:
        self.delete_webhook_calls.append(kwargs)
        return True


class FakeDispatcher:
    def resolve_used_update_types(self) -> list[str]:
        return ["message"]


def production_settings(make_settings: Callable[..., Settings]) -> Settings:
    return make_settings(
        environment=Environment.PRODUCTION,
        webhook_base_url="https://bot.example.com",
        webhook_secret="webhook-secret",
        drop_pending_updates=True,
    )


def test_production_startup_sets_webhook(
    make_settings: Callable[..., Settings],
) -> None:
    bot = FakeBot()

    asyncio.run(on_startup(bot, FakeDispatcher(), production_settings(make_settings)))

    assert bot.set_webhook_calls == [
        {
            "url": "https://bot.example.com/webhook",
            "secret_token": "webhook-secret",
            "drop_pending_updates": True,
            "allowed_updates": ["message"],
        },
    ]
    assert bot.delete_webhook_calls == []


def test_local_startup_deletes_webhook(make_settings: Callable[..., Settings]) -> None:
    bot = FakeBot()

    asyncio.run(on_startup(bot, FakeDispatcher(), make_settings()))

    assert bot.delete_webhook_calls == [{"drop_pending_updates": False}]
    assert bot.set_webhook_calls == []


def test_production_shutdown_deletes_webhook(
    make_settings: Callable[..., Settings],
) -> None:
    bot = FakeBot()

    asyncio.run(on_shutdown(bot, production_settings(make_settings)))

    assert bot.delete_webhook_calls == [{}]


def test_local_shutdown_keeps_webhook_untouched(
    make_settings: Callable[..., Settings],
) -> None:
    bot = FakeBot()

    asyncio.run(on_shutdown(bot, make_settings()))

    assert bot.delete_webhook_calls == []
