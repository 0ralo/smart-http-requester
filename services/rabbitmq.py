import aio_pika

from config import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_VHOST

_rabbitmq = None

async def get_rabbitmq():
    global _rabbitmq
    if _rabbitmq is None:
        _rabbitmq = await aio_pika.connect_robust(f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}")
    return _rabbitmq

