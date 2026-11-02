from __future__ import annotations

import logging
import sys

import structlog

from src.core.config import LogFormat, LogLevel

_SHARED_PROCESSORS: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
]


def setup_logging(level: LogLevel, log_format: LogFormat) -> None:
    """
    Configure structlog and the stdlib root logger.

    Purpose:
        Sets up structlog to emit records through a stdlib ``ProcessorFormatter``
        so structlog and standard-library loggers share one output format.

    Args:
        level: Minimum level applied to the root logger.
        log_format: Rendering format; ``"json"`` produces JSON records while
            ``"console"`` renders human-readable output.

    Notes:
        - Clears the root logger's existing handlers and replaces them with a
          single stdout ``StreamHandler`` using the configured formatter.
        - Stdlib records pass through the shared processors as a foreign
          pre-chain.
        - Console output enables colors only when stdout is a TTY; JSON output
          renders exception tracebacks as dictionaries.
        - structlog caches bound loggers on first use.
    """
    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    if log_format == "json":
        renderer: structlog.typing.Processor = structlog.processors.JSONRenderer()
        processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.dict_tracebacks,
            renderer,
        ]
    else:
        processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()),
        ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=processors,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
