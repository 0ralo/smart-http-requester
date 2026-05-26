import ssl
from typing import Union

import aio_pika

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
        ssl_ctx = None
        if settings.rabbitmq_use_ssl and settings.rabbitmq_ca_cert:
            ssl_ctx = ssl.create_default_context(cafile=settings.rabbitmq_ca_cert)
            if settings.rabbitmq_cert and settings.rabbitmq_key:
                ssl_ctx.load_cert_chain(certfile=settings.rabbitmq_cert, keyfile=settings.rabbitmq_key)

        url = f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}/{settings.rabbitmq_vhost}"
        _rabbitmq = await aio_pika.connect_robust(url, ssl=ssl_ctx)
    return _rabbitmq


async def close_rabbitmq() -> None:
    global _rabbitmq
    if _rabbitmq is not None and not _rabbitmq.is_closed:
        await _rabbitmq.close()
    _rabbitmq = None


async def ensure_structure(max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> None:
    max_attempts = min(max_attempts, MAX_ATTEMPTS_LIMIT)
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
    channel = await conn.channel()
    main_ex = await channel.declare_exchange(TASK_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)
    body = payload if isinstance(payload, bytes) else str(payload).encode()
    message = aio_pika.Message(body=body, headers={"attempts": attempts})
    await main_ex.publish(message, routing_key=TASK_QUEUE)
    await channel.close()
