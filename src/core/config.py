from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal, Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SECRET_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,256}")


class Environment(StrEnum):
    """Runtime mode of the bot: local long polling or production webhook."""

    LOCAL = "local"
    PRODUCTION = "production"


LogFormat = Literal["console", "json"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and the `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Environment = Environment.LOCAL
    bot_token: SecretStr

    log_level: LogLevel = "INFO"
    log_format: LogFormat | None = None

    webhook_base_url: str | None = None
    webhook_path: str = "/webhook"
    webhook_secret: SecretStr | None = None
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080
    drop_pending_updates: bool = False

    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        """
        Normalize the log level to uppercase.

        Purpose:
            Allows log level values to be provided in any case before validation.

        Args:
            value: Raw field value to normalize.

        Returns:
            object: The uppercased string when `value` is a string, otherwise the
                value unchanged.
        """
        if isinstance(value, str):
            return value.upper()
        return value

    @field_validator("webhook_base_url", mode="before")
    @classmethod
    def normalize_base_url(cls, value: object) -> object:
        """
        Normalize the webhook base URL.

        Purpose:
            Trims surrounding whitespace, removes the trailing slash, and converts
            an empty string to `None`.

        Args:
            value: Raw field value to normalize.

        Returns:
            object: The normalized string, `None` for an empty string, or the value
                unchanged when it is not a string.
        """
        if isinstance(value, str):
            value = value.strip().rstrip("/")
            return value or None
        return value

    @field_validator("webhook_base_url")
    @classmethod
    def validate_webhook_base_url(cls, value: str | None) -> str | None:
        """
        Validate the webhook base URL scheme.

        Purpose:
            Ensures that the configured base URL uses HTTP or HTTPS.

        Args:
            value: Base URL to validate, or `None` when it is not configured.

        Returns:
            str | None: The validated URL or `None`.

        Raises:
            ValueError: If the URL does not start with `http://` or `https://`.
        """
        if value is not None and not value.startswith(("http://", "https://")):
            raise ValueError("WEBHOOK_BASE_URL must be a valid HTTP(S) URL")
        return value

    @field_validator("webhook_path", mode="before")
    @classmethod
    def validate_webhook_path(cls, value: object) -> object:
        """
        Validate the webhook path.

        Purpose:
            Trims surrounding whitespace and ensures that string paths are absolute.

        Args:
            value: Raw field value to validate.

        Returns:
            object: The trimmed string when `value` is a string, otherwise the value
                unchanged.

        Raises:
            ValueError: If a string path does not start with `/`.
        """
        if isinstance(value, str):
            value = value.strip()
            if not value.startswith("/"):
                raise ValueError("WEBHOOK_PATH must start with '/'")
        return value

    @field_validator("webhook_secret", mode="before")
    @classmethod
    def normalize_webhook_secret(cls, value: object) -> object:
        """
        Normalize the webhook secret.

        Purpose:
            Trims surrounding whitespace and converts an empty string to `None`.

        Args:
            value: Raw field value to normalize.

        Returns:
            object: The trimmed string, `None` for an empty string, or the value
                unchanged when it is not a string.
        """
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, value: SecretStr | None) -> SecretStr | None:
        """
        Validate the webhook secret format.

        Purpose:
            Ensures that a configured secret matches the allowed character set and
            length.

        Args:
            value: Secret to validate, or `None` when it is not configured.

        Returns:
            SecretStr | None: The validated secret or `None`.

        Raises:
            ValueError: If the secret is not 1-256 characters from `A-Z`, `a-z`,
                `0-9`, `_`, or `-`.
        """
        if value is None:
            return value
        secret = value.get_secret_value()
        if not _SECRET_PATTERN.fullmatch(secret):
            raise ValueError(
                "WEBHOOK_SECRET must contain 1-256 characters: "
                "A-Z, a-z, 0-9, '_' or '-'",
            )
        return value

    @field_validator("redis_url", mode="before")
    @classmethod
    def normalize_redis_url(cls, value: object) -> object:
        """
        Normalize the Redis URL.

        Purpose:
            Trims surrounding whitespace before validation.

        Args:
            value: Raw field value to normalize.

        Returns:
            object: The trimmed string when `value` is a string, otherwise the value
                unchanged.
        """
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: SecretStr) -> SecretStr:
        """
        Validate the Redis URL scheme.

        Purpose:
            Ensures that the Redis DSN uses a supported scheme.

        Args:
            value: Redis URL to validate.

        Returns:
            SecretStr: The validated Redis URL.

        Raises:
            ValueError: If the DSN does not start with `redis://` or `rediss://`.
        """
        dsn = value.get_secret_value()
        if not dsn.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must start with 'redis://' or 'rediss://'")
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        """
        Validate settings required in the production environment.

        Purpose:
            Ensures that webhook configuration is present when the bot runs in
            production.

        Returns:
            Self: The validated settings instance.

        Raises:
            ValueError: If `WEBHOOK_BASE_URL` or `WEBHOOK_SECRET` is missing in
                production.

        Notes:
            - Returns immediately when the environment is not production.
        """
        if self.environment is not Environment.PRODUCTION:
            return self
        if not self.webhook_base_url:
            raise ValueError("WEBHOOK_BASE_URL is required in production")
        if self.webhook_secret is None:
            raise ValueError("WEBHOOK_SECRET is required in production")
        return self

    @property
    def resolved_log_format(self) -> LogFormat:
        """
        Resolve the effective log format.

        Purpose:
            Uses the explicitly configured format or defaults to `json` in
            production and `console` otherwise.

        Returns:
            LogFormat: The resolved log format.
        """
        if self.log_format is not None:
            return self.log_format
        return "json" if self.environment is Environment.PRODUCTION else "console"

    @property
    def webhook_url(self) -> str | None:
        """
        Build the full webhook URL.

        Purpose:
            Combines the webhook base URL with the webhook path.

        Returns:
            str | None: The full webhook URL, or `None` when the base URL is not
                configured.
        """
        if not self.webhook_base_url:
            return None
        return f"{self.webhook_base_url}{self.webhook_path}"

    @property
    def webhook_secret_value(self) -> str | None:
        """
        Expose the webhook secret as plain text.

        Purpose:
            Provides the secret value for webhook registration.

        Returns:
            str | None: The secret value, or `None` when it is not configured.
        """
        if self.webhook_secret is None:
            return None
        return self.webhook_secret.get_secret_value()

    @property
    def redis_dsn(self) -> str:
        """
        Expose the Redis DSN as plain text.

        Purpose:
            Provides the Redis connection string for storage setup.

        Returns:
            str: The Redis connection string.
        """
        return self.redis_url.get_secret_value()
