import redis.asyncio as redis

from config import settings
from services.logger import logger

_redis_client: redis.Redis | None = None

async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        logger.debug("Creating Redis client")
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=0,
            decode_responses=True,
            socket_connect_timeout=3,
        )
    return _redis_client

async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        logger.debug("Closing Redis client")
        await _redis_client.close()
        await _redis_client.wait_closed()
        _redis_client = None