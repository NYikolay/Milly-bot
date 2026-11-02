import json
import logging

import pytest
import structlog

from src.core.logging import setup_logging


def test_structlog_event_is_rendered_as_json(
    capsys: pytest.CaptureFixture[str],
    restore_logging: None,
) -> None:
    setup_logging("INFO", "json")

    structlog.get_logger("test").info("hello", user_id=7)

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["event"] == "hello"
    assert payload["level"] == "info"
    assert payload["logger"] == "test"
    assert payload["user_id"] == 7


def test_stdlib_log_record_is_rendered_as_json(
    capsys: pytest.CaptureFixture[str],
    restore_logging: None,
) -> None:
    setup_logging("INFO", "json")

    logging.getLogger("aiogram.test").warning("stdlib message")

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["event"] == "stdlib message"
    assert payload["level"] == "warning"
    assert payload["logger"] == "aiogram.test"
