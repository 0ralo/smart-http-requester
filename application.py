from contextlib import asynccontextmanager

from fastapi import FastAPI
from api.v1 import router as router_v1

from services.database import database_ping
from services.logger import logger
from services.redis import close_redis, get_redis
from services.rabbitmq import close_rabbitmq, get_rabbitmq
from middleware.metrics import MetricsMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    # before start
    await pre_check()
    # server is online
    yield
    # before shutdown
    await pre_shutdown()


async def pre_check():
    logger.info("Server is starting")
    try:
        await (await get_redis()).ping()
        logger.debug("Redis connection is established")
        await database_ping()
        logger.debug("Database connection is established")
        await get_rabbitmq()
        logger.debug("RabbitMQ connection is established")
    except Exception:
        logger.exception("Startup pre-check failed")
        raise


async def pre_shutdown():
    logger.info("Server is shutting down")
    try:
        await close_rabbitmq()
        await close_redis()
    except Exception:
        logger.exception("Shutdown cleanup failed")


app = FastAPI(
    title="HTTP-requester API documentation",
    lifespan=lifespan,
    openapi_url="/api/openapi.json"
)

# Add metrics middleware to collect HTTP metrics
app.add_middleware(MetricsMiddleware)

app.include_router(router_v1)
