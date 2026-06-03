import asyncio
import json

import asyncpg

from config import settings
from services.redis import get_redis

# Global reference to redis for the listener callback
_redis_for_listener = None


async def start_pg_listener(app):
    """Background task: listen to Postgres NOTIFY for task status changes.
    
    Connects to Postgres using asyncpg and listens to 'task_status_change' channel.
    Publishes received notifications to Redis 'tasks.status' channel.
    """
    global _redis_for_listener
    
    postgres_dsn = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
    
    conn = None
    redis = None
    
    while True:
        try:
            # connect to postgres if needed
            if conn is None:
                try:
                    conn = await asyncpg.connect(postgres_dsn)
                    # add listener for task status changes
                    conn.add_listener('task_status_change', _on_task_status_change)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    conn = None
                    await asyncio.sleep(2)
                    continue
            
            # get redis connection if needed
            if redis is None:
                try:
                    redis = await get_redis()
                    _redis_for_listener = redis
                except Exception:
                    redis = None
                    await asyncio.sleep(2)
                    continue
            
            # keep connection alive
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            
        except asyncio.CancelledError:
            break
        except Exception:
            # unexpected error, reconnect
            if conn is not None:
                try:
                    await conn.close()
                except Exception:
                    pass
            conn = None
            await asyncio.sleep(2)
    
    # cleanup on shutdown
    if conn is not None:
        try:
            await conn.close()
        except Exception:
            pass


def _on_task_status_change(conn, pid, channel, message):
    """Callback for Postgres NOTIFY events.
    
    message is a JSON string: {"task_id":"...", "status":"...", "operation":"..."}
    """
    global _redis_for_listener
    try:
        if _redis_for_listener is not None:
            # schedule async publish
            asyncio.create_task(_publish_to_redis_async(message))
    except Exception:
        pass


async def _publish_to_redis_async(message: str):
    """Publish received notification to Redis."""
    global _redis_for_listener
    try:
        if _redis_for_listener is not None:
            await _redis_for_listener.publish("tasks.status", message)
    except Exception:
        pass
