import redis.asyncio as redis

from config import settings
import ssl

_redis_client: redis.Redis | None = None

async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        ssl_params = {}
        if settings.redis_use_ssl and settings.redis_ca_cert:
            ssl_ctx = ssl.create_default_context(cafile=settings.redis_ca_cert)
            if settings.redis_cert and settings.redis_key:
                ssl_ctx.load_cert_chain(certfile=settings.redis_cert, keyfile=settings.redis_key)
            ssl_params = {"ssl": True, "ssl_ca_certs": settings.redis_ca_cert, "ssl_certfile": settings.redis_cert, "ssl_keyfile": settings.redis_key}

        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=0,
            decode_responses=True,
            socket_connect_timeout=3,
            **(ssl_params or {})
        )
    return _redis_client

async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        await _redis_client.wait_closed()
        _redis_client = None