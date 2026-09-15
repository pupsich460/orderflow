# OrderFlow

Event-driven система на 3 микросервисах, демонстрирующая асинхронную коммуникацию через message broker вместо прямых HTTP-вызовов между сервисами.

![Tests](https://github.com/pupsich460/orderflow/actions/workflows/tests.yml/badge.svg)

## Идея

Заказ (тестовая сущность) проходит путь через несколько независимых сервисов, не знающих друг о друге напрямую — они общаются только через очереди RabbitMQ:

```
Client → [api] → orders_queue → [worker] → notifications_queue → [notifier] → Telegram
                     │                │
                     ▼                ▼
                 Postgres      orders_queue_dlq (после 3 неудачных попыток)
```

- **api** — принимает заказ через REST API, сохраняет в БД со статусом `pending`, публикует событие в очередь
- **worker** — слушает очередь заказов, обрабатывает заказ, меняет статус на `processed`, публикует событие о результате
- **notifier** — слушает очередь уведомлений, отправляет сообщение в Telegram

Сервисы физически независимы: `api` и `worker` могут упасть, перезапуститься или масштабироваться отдельно друг от друга — RabbitMQ гарантирует, что сообщение не потеряется между этим.

## Надёжность

- **Retry + Dead Letter Queue** — при ошибке обработки сообщение переотправляется в `orders_queue` до 3 раз (счётчик хранится в заголовках сообщения), после чего уходит в `orders_queue_dlq` вместо бесконечного цикла
- **Idempotency** — worker проверяет `order.status` перед обработкой; если заказ уже `processed`, сообщение подтверждается без повторной обработки — защита от дублей при at-least-once доставке
- **Alembic-миграции** — схема БД версионируется через миграции, а не пересоздаётся на каждый старт

## Стек

- **FastAPI** — REST API
- **SQLAlchemy (async) + asyncpg** — работа с БД
- **PostgreSQL** — хранение заказов
- **Alembic** — миграции БД (через psycopg2, отдельно от async-рантайма)
- **RabbitMQ (aio-pika)** — брокер сообщений между сервисами
- **aiogram** — отправка уведомлений в Telegram
- **pytest + httpx** — тесты API-эндпоинтов на мокнутой сессии
- **ruff** — линтер и форматтер
- **GitHub Actions** — CI (lint + tests на каждый push/PR)
- **Docker Compose** — оркестрация всех сервисов

## Структура проекта

```
orderflow/
├── docker-compose.yml
├── .env                    # переменные окружения (не в git)
├── .github/workflows/
│   └── tests.yml            # CI: ruff + pytest
├── shared/                  # общие SQLAlchemy-модели и логгер, используются api и worker
│   ├── models.py
│   ├── database.py
│   └── logger.py
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── tests/
│   │   └── test_orders.py
│   └── app/
│       ├── main.py
│       ├── rabbitmq.py      # publish в orders_queue
│       ├── routers/
│       └── schemas/
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py          # consumer orders_queue (retry/DLQ, idempotency) + publish в notifications_queue
└── notifier/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        └── main.py          # consumer notifications_queue + Telegram
```

## Запуск

1. Склонируй репозиторий и создай `.env` в корне:

```
POSTGRES_USER=orderflow
POSTGRES_PASSWORD=orderflow
POSTGRES_DB=orderflow
RABBITMQ_USER=orderflow
RABBITMQ_PASSWORD=orderflow
BOT_API_TOKEN=<токен от BotFather>
TELEGRAM_CHAT_ID=<твой chat_id>
```

2. Запусти:

```bash
docker compose up --build
```

Миграции применяются автоматически при старте `api` (`alembic upgrade head` перед запуском uvicorn).

3. Открой Swagger-документацию API: [http://localhost:8000/docs](http://localhost:8000/docs)

4. Создай заказ через `POST /v1/orders/`:

```json
{
  "item": "Наушники",
  "qty": 2
}
```

5. Проверь:
   - RabbitMQ Management UI: [http://localhost:15672](http://localhost:15672) (логин/пароль из `.env`) — очереди `orders_queue`, `notifications_queue`, `orders_queue_dlq`
   - Статус заказа в БД сменится на `processed`
   - В Telegram придёт уведомление от бота

## Тесты

```bash
cd api
pytest
```

Тесты используют мокнутую БД-сессию (через `app.dependency_overrides`) и не требуют поднятой инфраструктуры — поэтому прогоняются и в CI без Docker.

## Что дальше можно добавить

- Тесты для worker и notifier (сейчас покрыт только api)
- Полноценный async Alembic env.py вместо отдельного sync-драйвера
- Метрики / health-check эндпоинты