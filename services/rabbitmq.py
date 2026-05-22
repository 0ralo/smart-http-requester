import aio_pika

from config import settings

_rabbitmq: aio_pika.RobustConnection | None = None

async def get_rabbitmq():
    global _rabbitmq
    if _rabbitmq is None or _rabbitmq.is_closed:
        _rabbitmq = await aio_pika.connect_robust(
            f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}/{settings.rabbitmq_vhost}"
        )
    return _rabbitmq

async def close_rabbitmq() -> None:
    global _rabbitmq
    if _rabbitmq is not None and not _rabbitmq.is_closed:
        await _rabbitmq.close()
    _rabbitmq = None

