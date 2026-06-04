import asyncio
import asyncpg

from config import settings
from services.redis import get_redis

_redis_for_listener = None


async def start_pg_listener(app):
    """Background task: listen to Postgres NOTIFY and publish task status updates to Redis."""
    global _redis_for_listener

    conn = None
    redis = None

    async def connect():
        return await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_database,
        )

    while True:
        try:
            if conn is None:
                conn = await connect()
                conn.add_listener("task_status_change", _on_task_status_change)

            if redis is None:
                redis = await get_redis()
                _redis_for_listener = redis

            await asyncio.sleep(10)
        except asyncio.CancelledError:
            break
        except Exception:
            if conn is not None:
                try:
                    await conn.close()
                except Exception:
                    pass
            conn = None
            await asyncio.sleep(2)

    if conn is not None:
        try:
            await conn.close()
        except Exception:
            pass


def _on_task_status_change(conn, pid, channel, payload):
    if _redis_for_listener is None:
        return
    try:
        asyncio.create_task(_publish_to_redis(payload))
    except Exception:
        pass


async def _publish_to_redis(payload: str):
    if _redis_for_listener is None:
        return
    try:
        await _redis_for_listener.publish("tasks.status", payload)
    except Exception:
        pass
