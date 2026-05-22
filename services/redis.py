import redis.asyncio as redis

from config import settings

_redis_client: redis.Redis | None = None

async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=0,
            decode_responses=True,
            socket_connect_timeout=3
        )
    return _redis_client

async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        await _redis_client.wait_closed()
        _redis_client = None