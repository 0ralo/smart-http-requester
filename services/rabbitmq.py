from typing import Union

import aio_pika
from loguru import logger

from config import settings

_rabbitmq: aio_pika.RobustConnection | None = None

# Naming/structure constants
TASK_EXCHANGE = "tasks.exchange"
TASK_QUEUE = "tasks.queue"
DLX_EXCHANGE = "tasks.dlx"
DLQ_QUEUE = "tasks.dlq"
DEFAULT_MAX_ATTEMPTS = 5
MAX_ATTEMPTS_LIMIT = 20


async def get_rabbitmq():
    global _rabbitmq
    if _rabbitmq is None or _rabbitmq.is_closed:
        url = f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}/{settings.rabbitmq_vhost}"
        _rabbitmq = await aio_pika.connect_robust(url)
    return _rabbitmq


async def close_rabbitmq() -> None:
    global _rabbitmq
    if _rabbitmq is not None and not _rabbitmq.is_closed:
        await _rabbitmq.close()
    _rabbitmq = None


async def ensure_structure() -> None:
    conn = await get_rabbitmq()
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=10)

    main_ex = await channel.declare_exchange(TASK_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)
    dlx_ex = await channel.declare_exchange(DLX_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)

    dlq = await channel.declare_queue(DLQ_QUEUE, durable=True)
    await dlq.bind(dlx_ex, routing_key=DLQ_QUEUE)

    arguments = {
        "x-dead-letter-exchange": DLX_EXCHANGE,
        "x-dead-letter-routing-key": DLQ_QUEUE,
    }
    task_q = await channel.declare_queue(TASK_QUEUE, durable=True, arguments=arguments)
    await task_q.bind(main_ex, routing_key=TASK_QUEUE)

    await channel.close()


async def publish_task(payload: Union[bytes, str], attempts: int = 0) -> None:
    conn = await get_rabbitmq()
    try:
        async with conn.channel() as channel:
            main_ex = await channel.declare_exchange(TASK_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)
            body = payload if isinstance(payload, bytes) else str(payload).encode()
            message = aio_pika.Message(body=body, headers={"x-attempts": attempts, "x-attempts-done": 0})
            await main_ex.publish(message, routing_key=TASK_QUEUE)
    except Exception as e:
        logger.error(e)
        raise e
