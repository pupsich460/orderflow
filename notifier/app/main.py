import asyncio
import json
import os

import aio_pika
from aiogram import Bot

from shared.logger import get_logger

logger = get_logger(__name__)

BOT_API_TOKEN = os.getenv("BOT_API_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=BOT_API_TOKEN)

async def main():
    connection = await aio_pika.connect_robust("amqp://orderflow:orderflow@rabbitmq/")

    async with connection:
        channel = await connection.channel()

        queue = await channel.declare_queue("notifications_queue")

        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                body = json.loads(message.body)
                order_id = body["order_id"]
                status = body["status"]
                processed_message = f"Order with ID: {order_id} has been {status}."
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=processed_message)
                logger.info(f"Notification sent for order ID: {order_id} with status: {status}")

        await queue.consume(process_message)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())