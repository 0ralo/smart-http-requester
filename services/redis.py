import redis.asyncio as redis
from config import settings
import ssl
import logging

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        try:
            if settings.redis_use_ssl:
                logger.info(f"Connecting to Redis with SSL at {settings.redis_host}:{settings.redis_port}")

                # Use legacy SSL parameters that work with older redis-py
                _redis_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    ssl=True,  # Enable SSL
                    ssl_cert_reqs=ssl.CERT_NONE,  # Don't verify cert in dev
                    ssl_ca_certs=settings.redis_ca_cert,
                    ssl_certfile=settings.redis_cert,
                    ssl_keyfile=settings.redis_key,
                    ssl_check_hostname=False,  # Don't check hostname
                )
            else:
                logger.info(f"Connecting to Redis without SSL at {settings.redis_host}:{settings.redis_port}")
                _redis_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                )

            # Test connection
            await _redis_client.ping()
            logger.info("✅ Successfully connected to Redis")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            _redis_client = None
            raise

    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.close()
            await _redis_client.wait_closed()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None