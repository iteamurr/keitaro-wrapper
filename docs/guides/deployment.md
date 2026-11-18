# Развёртывание

[Все документы](../README.md)

Команды выполняются из корня проекта.

Нужен Docker с Compose. Подготовьте локальные настройки:

```sh
cp .env.example .env
```

В `.env` задайте разные случайные значения `POSTGRES_PASSWORD` и
`APP_SECRET_KEY` (не менее 32 символов). Для пароля БД используйте URL-safe
символы, поскольку Compose включает его в URL подключения. Получить случайное
значение можно командой `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`.

Для работы с Keitaro заполните `KEITARO_BASE_URL` — только HTTPS origin,
например `https://tracker.example.invalid`, без `/admin` — и `KEITARO_API_KEY`.
Ключ хранится только в окружении. Пустой ключ позволяет открыть локальный
редактор, но запросы интеграции завершатся объяснимой ошибкой.

```sh
docker compose build
docker compose up -d db
docker compose run --rm app alembic upgrade head
docker compose up -d app
```

Откройте <http://127.0.0.1:8000>. Миграцию запускают явно перед первым стартом
и после обновлений со схемой БД. Приложение не применяет её автоматически.
Compose подставляет свой `DATABASE_URL`; значение из `.env` нужно для запуска
Python на хосте. Порт PostgreSQL наружу не опубликован.

```sh
docker compose logs --tail=100 app
docker compose down
```

Остановка сохраняет данные в named volume. Команда `down -v` удаляет БД,
включая черновики и историю операций.

## Сборка образа напрямую

```sh
docker build -f deploy/Dockerfile -t keitaro-wrapper:local .
```
