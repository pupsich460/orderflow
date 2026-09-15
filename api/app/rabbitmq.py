import json

import aio_pika


async def publish_order(order_id: int):
    connection = await aio_pika.connect_robust("amqp://orderflow:orderflow@rabbitmq/")

    async with connection:
        channel = await connection.channel()

        queue = await channel.declare_queue(
            "orders_queue",
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": "orders_queue_dlq",
            },
        )

        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps({"order_id": order_id}).encode()),
            routing_key=queue.name,
        )
