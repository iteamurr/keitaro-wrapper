# Разработка и проверки

[Все документы](../README.md)

Команды выполняются из корня проекта.

Нужны Python 3.13, uv и доступная PostgreSQL 17. Укажите её URL в `.env`:
`postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB`.

```sh
uv sync --locked
uv run --env-file .env alembic upgrade head
uv run uvicorn keitaro_wrapper.main:create_app --factory --host 127.0.0.1 --port 8000
```

Одна БД обслуживается одним процессом с одним Uvicorn worker. Блокировка
PostgreSQL не допускает второй экземпляр. БД привязывается к origin Keitaro
при первом старте: смена `KEITARO_BASE_URL` требует отдельной БД.

`/health/live` проверяет процесс, `/health/ready` — доступность БД и версию
миграции. Они не проверяют Keitaro. Контракт API доступен по `/openapi.json`;
команды используют подписанную сессию, `X-CSRF-Token` из `/api/v1/bootstrap`
и UUID в `Idempotency-Key`. Повтор той же команды использует прежний ключ.

## Проверки

Статические проверки и домен/HTTP gateway не требуют БД:

```sh
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest tests/unit -q
```

Для полного набора нужна отдельная одноразовая БД с именем `test_*`.
**Тесты очищают её таблицы.** Пример запуска изолированной PostgreSQL:

```sh
docker run --rm -d --name keitaro-wrapper-tests -p 127.0.0.1:55432:5432 \
  -e POSTGRES_USER=wrapper -e POSTGRES_PASSWORD=wrapper \
  -e POSTGRES_DB=test_keitaro postgres:17-alpine
docker exec keitaro-wrapper-tests pg_isready -U wrapper -d test_keitaro
export TEST_DATABASE_URL=postgresql+asyncpg://wrapper:wrapper@127.0.0.1:55432/test_keitaro
uv run pytest -q
```

Начинайте pytest после готовности PostgreSQL. Тесты сами применяют миграцию
только к тестовой БД. Пароль выше относится исключительно к одноразовой БД
с синтетическими данными. Живой Keitaro обычные тесты не вызывают.

Браузерная проверка использует отдельный тестовый сервер, который также
очищает `TEST_DATABASE_URL`. Не запускайте его одновременно с pytest:

```sh
uv run playwright install chromium
uv run uvicorn tests.browser.app:browser_app --factory --host 127.0.0.1 --port 8008
```

В другом терминале: `uv run python -m tests.browser.smoke`. Сценарий проверяет
сохранение черновика, Cancel, Remove/Push/Bring Back, создание, ссылку кампании,
JavaScript-ошибки и отсутствие горизонтального переполнения на ширине 390px.
Снимки остаются в игнорируемой `.impeccable/review/`.
Дополнительный сценарий `uv run python -m tests.browser.recovery` проверяет
потерю ответа после создания, повтор с тем же ключом, отклонённый повтор,
некорректный успешный ответ и ошибку обновления экрана после выполненной команды.
Перед повторным запуском сценариев перезапустите тестовый сервер для очистки данных.
Для скриншотов README перезапустите тестовый сервер и выполните
`uv run python -m tests.browser.showcase`. Сценарий сохраняет реальные экраны
в `docs/assets/screenshots/`; данные демонстрационные.
[Результаты последней проверки](validation.md) отделены от инструкций запуска.

После проверок остановите тестовый сервер и `docker stop keitaro-wrapper-tests`.
