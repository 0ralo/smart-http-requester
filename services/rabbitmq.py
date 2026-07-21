from typing import Union

import aio_pika
from aio_pika import ExchangeType

from config import settings
from services.logger import logger

_rabbitmq: aio_pika.RobustConnection | None = None

# Naming/structure constants
TASK_EXCHANGE = "tasks.exchange"
TASK_QUEUE = "tasks.queue"
DLX_EXCHANGE = "tasks.dlx"
DLQ_QUEUE = "tasks.dlq"
DEFAULT_MAX_ATTEMPTS = 5
MAX_ATTEMPTS_LIMIT = 20
RETRY_QUEUES = {
    1: {"name": "tasks.retry.1s", "ttl": 1000},
    2: {"name": "tasks.retry.2s", "ttl": 2000},
    3: {"name": "tasks.retry.4s", "ttl": 4000},
    4: {"name": "tasks.retry.8s", "ttl": 8000},
    5: {"name": "tasks.retry.16s", "ttl": 16000},
    6: {"name": "tasks.retry.32s", "ttl": 32000},
    7: {"name": "tasks.retry.64s", "ttl": 64000},
}


async def get_rabbitmq():
    global _rabbitmq
    if _rabbitmq is None or _rabbitmq.is_closed:
        logger.debug("Connecting to RabbitMQ")
        url = f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}/{settings.rabbitmq_vhost}"
        _rabbitmq = await aio_pika.connect_robust(url)
        logger.debug("RabbitMQ connection established")
    return _rabbitmq


async def close_rabbitmq() -> None:
    global _rabbitmq
    if _rabbitmq is not None and not _rabbitmq.is_closed:
        logger.debug("Closing RabbitMQ connection")
        await _rabbitmq.close()
    _rabbitmq = None


async def setup_rabbitmq_with_retries() -> None:
    logger.info("Ensuring RabbitMQ task structure")
    conn = await get_rabbitmq()
    channel = await conn.channel()
    try:
        await channel.set_qos(prefetch_count=10)

        main_ex = await channel.declare_exchange(
            TASK_EXCHANGE, ExchangeType.DIRECT, durable=True
        )
        dlx_ex = await channel.declare_exchange(
            DLX_EXCHANGE, ExchangeType.DIRECT, durable=True
        )

        main_queue_args = {
            "x-dead-letter-exchange": DLX_EXCHANGE,
            "x-dead-letter-routing-key": "retry.1s",
        }
        task_queue = await channel.declare_queue(
            TASK_QUEUE, durable=True, arguments=main_queue_args
        )
        await task_queue.bind(main_ex, routing_key=TASK_QUEUE)
        await task_queue.bind(dlx_ex, routing_key=TASK_QUEUE)

        for config in RETRY_QUEUES.values():
            queue_args = {
                "x-message-ttl": config["ttl"],
                "x-dead-letter-exchange": DLX_EXCHANGE,
                "x-dead-letter-routing-key": TASK_QUEUE,
            }
            queue = await channel.declare_queue(
                config["name"], durable=True, arguments=queue_args
            )
            await queue.bind(dlx_ex, routing_key=config["name"])
    finally:
        await channel.close()


async def ensure_structure(max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> None:
    logger.info("Ensuring RabbitMQ task structure with max_attempts=%s", max_attempts)
    await setup_rabbitmq_with_retries()


async def publish_task(payload: Union[bytes, str], attempts: int = 0) -> None:
    logger.debug("Publishing RabbitMQ task with attempts=%s", attempts)
    conn = await get_rabbitmq()
    channel = await conn.channel()
    try:
        main_ex = await channel.declare_exchange(
            TASK_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
        )
        body = payload if isinstance(payload, bytes) else str(payload).encode()
        message = aio_pika.Message(
            body=body, headers={"x-attempts": attempts, "x-attempts-done": 0}
        )
        await main_ex.publish(message, routing_key=TASK_QUEUE)
        logger.debug("RabbitMQ task published")
    except Exception:
        logger.exception("Failed to publish RabbitMQ task")
        raise
    finally:
        await channel.close()
