from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from loguru import logger
from api.v1 import router as router_v1

from services.database import database_ping
from services.redis import close_redis, get_redis
from services.rabbitmq import close_rabbitmq, get_rabbitmq
from middleware.metrics import MetricsMiddleware
from services.pg_poller import start_pg_listener
import asyncio
import json


@asynccontextmanager
async def lifespan(_: FastAPI):
    # before start
    await pre_check()
    # server is online
    yield
    # before shutdown
    await pre_shutdown()


async def pre_check():
    logger.add("logs/app.log", rotation="monthly", retention="3 month", compression="gz")
    logger.info("Server is starting")
    await (await get_redis()).ping()
    logger.debug("Redis connection is established")
    await database_ping()
    logger.debug("Database connection is established")
    await get_rabbitmq()
    logger.debug("RabbitMQ connection is established")
    # start Postgres LISTEN/NOTIFY listener background task
    app.state.pg_listener_task = asyncio.create_task(start_pg_listener(app))


async def pre_shutdown():
    logger.info("Server is shutting down")
    await close_rabbitmq()
    await close_redis()
    # stop pg listener
    task = getattr(app.state, "pg_listener_task", None)
    if task:
        task.cancel()
        try:
            await task
        except Exception:
            pass


app = FastAPI(
    title="HTTP-requester API documentation",
    lifespan=lifespan,
    openapi_url="/api/openapi.json"
)

# Add metrics middleware to collect HTTP metrics
app.add_middleware(MetricsMiddleware)

app.include_router(router_v1)


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that forwards task status changes from Redis pub/sub.

    Clients should connect to `/ws`. Server subscribes to `tasks.status` channel
    and forwards published messages as text JSON messages.
    """
    await websocket.accept()
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe('tasks.status')

    try:
        # listen for published messages and forward to websocket
        async for message in pubsub.listen():
            if message is None:
                continue
            # message is a dict like { 'type': 'message', 'pattern': None, 'channel': b'tasks.status', 'data': b'...'}
            mtype = message.get('type')
            if mtype != 'message':
                continue
            data = message.get('data')
            if isinstance(data, (bytes, bytearray)):
                try:
                    text = data.decode()
                except Exception:
                    text = str(data)
            else:
                text = str(data)

            try:
                await websocket.send_text(text)
            except WebSocketDisconnect:
                break
            except Exception:
                break

    finally:
        try:
            await pubsub.unsubscribe('tasks.status')
            await pubsub.close()
        except Exception:
            pass
