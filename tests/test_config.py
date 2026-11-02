import pytest
from pydantic import ValidationError

from src.core.config import Environment, Settings


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, bot_token="42:TEST", **overrides)


def test_production_requires_webhook_base_url() -> None:
    with pytest.raises(ValidationError, match="WEBHOOK_BASE_URL"):
        make_settings(
            environment=Environment.PRODUCTION,
            webhook_secret="webhook-secret",
        )


def test_production_requires_webhook_secret() -> None:
    with pytest.raises(ValidationError, match="WEBHOOK_SECRET"):
        make_settings(
            environment=Environment.PRODUCTION,
            webhook_base_url="https://bot.example.com",
        )


def test_webhook_url_joins_base_url_and_path() -> None:
    settings = make_settings(
        environment=Environment.PRODUCTION,
        webhook_base_url="https://bot.example.com/",
        webhook_path="/telegram",
        webhook_secret="webhook-secret",
    )

    assert settings.webhook_url == "https://bot.example.com/telegram"


def test_local_defaults_to_console_logs_and_no_webhook() -> None:
    settings = make_settings()

    assert settings.environment is Environment.LOCAL
    assert settings.resolved_log_format == "console"
    assert settings.webhook_url is None


def test_production_defaults_to_json_logs() -> None:
    settings = make_settings(
        environment=Environment.PRODUCTION,
        webhook_base_url="https://bot.example.com",
        webhook_secret="webhook-secret",
    )

    assert settings.resolved_log_format == "json"


def test_log_format_can_be_overridden() -> None:
    settings = make_settings(log_format="json")

    assert settings.resolved_log_format == "json"


def test_log_level_is_normalized_to_uppercase() -> None:
    settings = make_settings(log_level="debug")

    assert settings.log_level == "DEBUG"


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError, match="log_level"):
        make_settings(log_level="verbose")


def test_webhook_path_must_start_with_slash() -> None:
    with pytest.raises(ValidationError, match="WEBHOOK_PATH"):
        make_settings(webhook_path="webhook")


def test_webhook_base_url_must_have_scheme() -> None:
    with pytest.raises(ValidationError, match="WEBHOOK_BASE_URL"):
        make_settings(webhook_base_url="bot.example.com")


def test_invalid_webhook_secret_is_rejected() -> None:
    with pytest.raises(ValidationError, match="WEBHOOK_SECRET"):
        make_settings(
            environment=Environment.PRODUCTION,
            webhook_base_url="https://bot.example.com",
            webhook_secret="not a valid secret!",
        )


def test_settings_are_loaded_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "42:ENV")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("WEBHOOK_BASE_URL", "https://env.example.com")
    monkeypatch.setenv("WEBHOOK_SECRET", "env-secret")

    settings = Settings(_env_file=None)

    assert settings.bot_token.get_secret_value() == "42:ENV"
    assert settings.environment is Environment.PRODUCTION
    assert settings.webhook_url == "https://env.example.com/webhook"


def test_redis_url_defaults_to_localhost() -> None:
    settings = make_settings()

    assert settings.redis_dsn == "redis://localhost:6379/0"


def test_redis_url_is_loaded_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "rediss://redis.example.com:6380/1")

    settings = Settings(_env_file=None, bot_token="42:TEST")

    assert settings.redis_dsn == "rediss://redis.example.com:6380/1"


def test_invalid_redis_url_is_rejected() -> None:
    with pytest.raises(ValidationError, match="REDIS_URL"):
        make_settings(redis_url="http://localhost:6379/0")
