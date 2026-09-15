# OrderFlow

Event-driven система на 3 микросервисах, демонстрирующая асинхронную коммуникацию через message broker вместо прямых HTTP-вызовов между сервисами.

## Идея

Заказ (тестовая сущность) проходит путь через несколько независимых сервисов, не знающих друг о друге напрямую — они общаются только через очереди RabbitMQ:

```
Client → [api] → orders_queue → [worker] → notifications_queue → [notifier] → Telegram
                     │
                     └──> Postgres (статус заказа)
```

- **api** — принимает заказ через REST API, сохраняет в БД со статусом `pending`, публикует событие в очередь
- **worker** — слушает очередь заказов, обрабатывает заказ, меняет статус на `processed`, публикует событие о результате
- **notifier** — слушает очередь уведомлений, отправляет сообщение в Telegram

Сервисы физически независимы: `api` и `worker` могут упасть, перезапуститься или масштабироваться отдельно друг от друга — RabbitMQ гарантирует, что сообщение не потеряется между этим.

## Стек

- **FastAPI** — REST API
- **SQLAlchemy (async) + asyncpg** — работа с БД
- **PostgreSQL** — хранение заказов
- **RabbitMQ (aio-pika)** — брокер сообщений между сервисами
- **aiogram** — отправка уведомлений в Telegram
- **Docker Compose** — оркестрация всех сервисов

## Структура проекта

```
orderflow/
├── docker-compose.yml
├── .env                  # переменные окружения (не в git)
├── shared/                # общие SQLAlchemy-модели, используются api и worker
│   ├── models.py
│   └── database.py
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── rabbitmq.py    # publish в orders_queue
│       ├── routers/
│       └── schemas/
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py        # consumer orders_queue + publish в notifications_queue
└── notifier/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        └── main.py        # consumer notifications_queue + Telegram
```

## Запуск

1. Склонируй репозиторий и создай `.env` в корне на основе `.env.example`:

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

3. Открой Swagger-документацию API: [http://localhost:8000/docs](http://localhost:8000/docs)

4. Создай заказ через `POST /v1/orders/`:

```json
{
  "item": "Наушники",
  "qty": 2
}
```

5. Проверь:
   - RabbitMQ Management UI: [http://localhost:15672](http://localhost:15672) (логин/пароль из `.env`) — очереди `orders_queue` и `notifications_queue`
   - Статус заказа в БД сменится на `processed`
   - В Telegram придёт уведомление от бота
