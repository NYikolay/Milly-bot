import asyncio
from typing import cast

from aiohttp import web

from src.core.webhook import healthcheck


def test_healthcheck_returns_ok() -> None:
    response = asyncio.run(healthcheck(cast(web.Request, None)))

    assert response.status == 200
    assert response.text == "ok"
