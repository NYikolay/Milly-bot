# AGENTS.md

Инженерные правила и факты проекта Milly bot для coding-агентов.
Продуктовое описание — в `README.md`; в каталоге `bot/` он пока не создан, поэтому не выдумывай продуктовые детали.
Здесь — только конвенции работы с кодом и актуальное состояние проекта.

Обязательный процесс разработки — SOLID+KISS+TDD; докстринги обязательны и поддерживаются в актуальном состоянии.

## 1. Проект и запуск

- `bot/` — отдельный git-репозиторий (ветка `main`, коммитов пока нет, все файлы untracked). Соседние `backend/` и `frontend/` — другие части Milly.
- Python `>=3.11,<3.15`; Docker-образ собирается на `python:3.14-slim`. Менеджер зависимостей — Poetry 2.5.1, `poetry.toml` создаёт `.venv` внутри проекта.
- `src/` — сам Python-пакет. Импорты только `from src...`, точка входа — `python -m src`; не вкладывай код в `src/bot/`.
- Стек: aiogram 3.x (long polling / webhook), aiohttp, structlog, pydantic-settings, redis; тесты — pytest (dev-группа).
- Режим задаётся `ENVIRONMENT`: `local` → long polling, `production` → aiohttp webhook.

```bash
poetry install
.venv/bin/python -m src
.venv/bin/python -m pytest
pre-commit run --all-files
docker compose up --build
```

Для локального запуска нужен Redis на `REDIS_URL` (по умолчанию `redis://localhost:6379/0`); поднять только его — `docker compose up -d redis`.

## 2. Структура

```text
src/
  __main__.py            # main(): выбор polling/webhook
  core/
    config.py            # Settings, Environment, валидаторы
    bot.py               # create_bot(settings)
    dispatcher.py        # create_dispatcher(settings)
    storage.py           # create_storage(settings) -> RedisStorage
    lifetime.py          # on_startup / on_shutdown / register_lifetime
    webhook.py           # healthcheck, create_web_app, run_webhook
    logging.py           # setup_logging
  handlers/              # root router, common (/start, /help), errors
  middlewares/logging.py # LoggingMiddleware
  filters/ keyboards/ services/ states/ utils/  # пока пустые пакеты
tests/
Dockerfile
docker-compose.yml
```

- `handlers/__init__.py` собирает root router; новые фича-роутеры подключай там.
- `handlers/errors.py` логирует ошибки хендлеров и возвращает `True`, подавляя дальнейшую обработку.
- `LoggingMiddleware` — outer middleware на `dispatcher.update`, работает только с `Update`.

## 3. Конфигурация

`Settings` (pydantic-settings) читает `.env` в UTF-8; имена переменных case-insensitive, лишние переменные игнорируются. Секреты хранятся в `SecretStr` и наружу отдаются через свойства.

| Переменная | По умолчанию | Правила |
|---|---|---|
| `ENVIRONMENT` | `local` | `local` или `production` |
| `BOT_TOKEN` | — | обязательна |
| `LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`, регистр нормализуется |
| `LOG_FORMAT` | авто | `console` или `json`; local → console, production → json |
| `WEBHOOK_BASE_URL` | — | обязательна в production; http(s), trailing `/` отбрасывается |
| `WEBHOOK_PATH` | `/webhook` | должен начинаться с `/` |
| `WEBHOOK_SECRET` | — | обязателен в production; 1–256 символов `[A-Za-z0-9_-]` |
| `WEBHOOK_HOST` | `0.0.0.0` | адрес aiohttp-сервера |
| `WEBHOOK_PORT` | `8080` | порт aiohttp-сервера |
| `DROP_PENDING_UPDATES` | `false` | передаётся в `set_webhook`/`delete_webhook` |
| `REDIS_URL` | `redis://localhost:6379/0` | только `redis://` или `rediss://` |

- В production без `WEBHOOK_BASE_URL` или `WEBHOOK_SECRET` старт падает с `ValidationError`.
- `.env` gitignored; канонический шаблон — `.env.example`. Не хардкодь токены и URL в коде.
- В `docker-compose.yml` `REDIS_URL` переопределяется на `redis://redis:6379/0`.

## 4. Runtime и lifecycle

- `main()`: `Settings()` → `setup_logging()` → `run_polling()` для local или `run_webhook()` для production.
- `create_dispatcher(settings)` создаёт `Dispatcher` с `RedisStorage`, подключает `LoggingMiddleware`, root router и lifetime-хуки.
- Startup: local удаляет webhook; production вызывает `set_webhook` с URL, секретом, `drop_pending_updates` и `dispatcher.resolve_used_update_types()`.
- Shutdown: production удаляет webhook, local ничего не делает. **Не закрывай `RedisStorage` в lifetime**: `Dispatcher` сам регистрирует `fsm.close` в shutdown.
- Polling: `start_polling(close_bot_session=False)`, сессия бота закрывается в `finally`.
- Webhook: `setup_application()` вызывается **до** `SimpleRequestHandler.register()` — порядок важен для корректного shutdown; маршрут `/health` доступен всегда; `handle_in_background=False`.
- Логи: structlog + stdlib `ProcessorFormatter`; JSON в production, console в local. `LoggingMiddleware` биндит `update_id`, `update_type`, `user_id`, `chat_id` и пишет `duration_ms`.
- Parse mode по умолчанию — HTML; пользовательский текст экранируй (`html.escape`).

## 5. Тесты и проверки

- Все тесты — в `tests/`; запуск `.venv/bin/python -m pytest` (в `pyproject.toml`: `testpaths = ["tests"]`, `pythonpath = ["."]`).
- `pytest-asyncio` не установлен: асинхронные тесты пиши через `asyncio.run(...)`.
- `tests/conftest.py` автоматически очищает env-переменные; фикстуры `make_settings` и `restore_logging`. В тестах `Settings` создавай с `_env_file=None`, чтобы не читать локальный `.env`.
- Тесты не требуют живых Redis/Telegram: бот, диспетчер и сетевые вызовы подменяются фейками; `RedisStorage` проверяется по типу.
- Pre-commit: базовые hooks, ruff (с `--fix`), ruff-format, isort, `graphify update`; pytest запускается только на pre-push.
- `pre-commit run --all-files` не видит untracked-файлы. Пока коммитов нет, проверяй `pre-commit run --files $(git ls-files --others --exclude-standard)`.
- Перед завершением задачи: `pytest` + pre-commit; при изменениях Docker — `docker build -t milly-bot:dev .` и `docker compose config --quiet`.

## 6. Docker

- `Dockerfile` multi-stage: builder ставит Poetry 2.5.1 и зависимости (`--only main --no-root`) в `/app/.venv`; runtime копирует venv и `src`, работает non-root (`bot`), `PYTHONPATH=/app`, `EXPOSE 8080`, `CMD ["python", "-m", "src"]`. Тесты и `.env` в образ не попадают.
- `docker-compose.yml`: сервисы `bot` и `redis` (`redis:8-alpine`, AOF, named volume `redis-data`, healthcheck `redis-cli ping`).
- `bot` читает `.env`, получает `REDIS_URL=redis://redis:6379/0` и ждёт healthy Redis (`depends_on: condition: service_healthy`).
- Наружу проброшены `${WEBHOOK_PORT:-8080}` у бота и `127.0.0.1:6379` у Redis.
- Healthcheck бота проверяет `/health` только при `ENVIRONMENT=production`; в local команда просто завершается успешно.

## 7. Докстринги

Докстринги обязательны для всех новых функций, методов и классов. **Докстринг поддерживается в актуальном состоянии**: при изменении сигнатуры, поведения или состава исключений функции обновляй её докстринг в том же изменении. Устаревший или неверный докстринг — такой же дефект, как падающий тест.

Все функции, методы и классы в `src/` уже имеют докстринги; новые и изменяемые функции документируй сразу по шаблону ниже.

- Язык — английский; заголовки секций — как в шаблоне ниже. Русскоязычные докстринги старого кода приводи к шаблону при доработке соответствующего кода.
- Классы — однострочный докстринг: что представляет класс (сущность, DTO, ORM-таблица, исключение, use case, контракт `Protocol`).
- Секции адаптивные: summary + `Purpose` — всегда; `Args`, `Returns`, `Raises` — когда применимо; `Examples`, `Notes` — где добавляют ценность (не нужны у тривиальных `__init__`, property и Protocol-заглушек).
- `Raises` — только реально поднимаемые или явно пробрасываемые исключения; `Examples` — достоверные примеры, согласованные с кодом. Параметры, исключения и поведение не выдумывать.
- В `Notes` отражай границы транзакций («не коммитит; коммит — на вызывающем слое, запись через `flush()`»), сайд-эффекты, идемпотентность, поля, генерируемые БД.
- Методы `Protocol`/ABC-заглушек описывают контракт, который обязан выполнить реализатор; `Args`/`Returns` для них обязательны.

```python
def calculate_order_total(items: list[dict], discount_percent: float = 0) -> float:
    """
    Calculate the total order cost.

    Purpose:
        Sums item costs and applies the discount; used when generating receipts.

    Args:
        items: Order items, each a dict with "price" (float) and "quantity" (int).
        discount_percent: Discount from 0 to 100. Defaults to 0.

    Returns:
        float: Total cost rounded to 2 decimal places.

    Raises:
        ValueError: If `items` is empty or a price/quantity/percent is out of range.

    Examples:
        >>> calculate_order_total([{"price": 100.0, "quantity": 2}], discount_percent=10)
        180.0

    Notes:
        - Discount is applied before rounding; no side effects.
    """
```

## 8. graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
