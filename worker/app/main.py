import asyncio
import json

import aio_pika

from shared.database import async_session
from shared.logger import get_logger
from shared.models import Order

logger = get_logger(__name__)

async def main():
    connection = await aio_pika.connect_robust("amqp://orderflow:orderflow@rabbitmq/")

    async with connection:
        channel = await connection.channel()

        await channel.declare_queue(
            "orders_queue_dlq"
        )

        queue = await channel.declare_queue(
            "orders_queue",
            arguments={
                "x-dead-letter-exchange": "", "x-dead-letter-routing-key": "orders_queue_dlq"}
        )
        await channel.declare_queue(
            "notifications_queue"
        )
        async def process_message(message: aio_pika.IncomingMessage):
            try:
                body = json.loads(message.body)
                order_id = body["order_id"]
                async with async_session() as session:
                    order = await session.get(Order, order_id)
                    if order.status == "processed":
                        logger.info(f"Order with ID: {order_id} has already been processed. Acknowledging message.")
                        await message.ack()
                        return
                    order.status = "processed"
                    await session.commit()
                logger.info(f"Processed order with ID: {order_id}")
                await channel.default_exchange.publish(
                    aio_pika.Message(body=json.dumps({"order_id": order_id, "status": "processed"}).encode()),
                    routing_key="notifications_queue",
                )
                await message.ack()
            except Exception as e:  # noqa: BLE001 — ловим всё намеренно, чтобы любая ошибка ушла в retry/DLQ, а не уронила consumer
                retry_count = message.headers.get("x-retry-count", 0) if message.headers else 0
                logger.error(f"Ошибка обработки заказа: {e}, попытка {retry_count + 1}")

                if retry_count < 3:
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=message.body,
                            headers={"x-retry-count": retry_count + 1},
                        ),
                        routing_key="orders_queue",
                    )
                    await message.ack()
                else:
                    await message.reject(requeue=False)
        await queue.consume(process_message)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
