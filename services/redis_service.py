import time
from typing import Optional

import redis.asyncio as redis
from redis.commands.core import AsyncScript

from config import settings
from services.logger import logger

_redis_client = None


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
        _redis_client = None

script: Optional[AsyncScript] = None

async def get_script():
    global script
    if script is None:
        script = await init_script()
    return script

async def init_script():
    lua_script = """
            -- KEYS[1] = key ~ "rate_limit:user:004-redis-distributed-rate-limiting.en.md"
            -- ARGV[1] = limit
            -- ARGV[2] = window time (60 secs)
            -- ARGV[3] = time now

            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])

            local elapsed = now % window

            local current_key = key .. ":" .. math.floor(now / window)
            local previous_key = key .. ":" .. (math.floor(now / window) - 1)

            local current_count = tonumber(redis.call("GET", current_key) or "0")
            local previous_count = tonumber(redis.call("GET", previous_key) or "0")

            local weight = 1 - (elapsed / window)

            local total = current_count + (previous_count * weight)
            
            local reset_time = math.floor(now / window) * window + window

            if total >= limit then
                return {0, total, reset_time}
            else
                redis.call("INCR", current_key)
                redis.call("EXPIRE", current_key, window * 2)
                redis.call("EXPIRE", previous_key, window * 2)

                return {1, total + 1, reset_time}
            end
        """

    return (await get_redis()).register_script(lua_script)


async def check_rate_limit(key: str, limit: int = 100, window: int = 60) -> (bool, float, int):
    script = await get_script()
    now = int(time.time())
    result = await script(keys=[key], args=[limit, window, now])
    return result[0], result[1], result[2]

