import time
from typing import Optional

from redis.commands.core import AsyncScript

import services.redis as redis_module

_redis_client = None


async def get_redis():
    return await redis_module.get_redis()


async def close_redis() -> None:
    await redis_module.close_redis()

script: Optional[AsyncScript] = None

async def get_script():
    global script
    if script is None:
        script = await init_script()
    return script

async def init_script():
    lua_script = """
            -- KEYS[1] = key ~ "rate_limit:user:123"
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

