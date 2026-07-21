import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from api.v1 import router as router_v1
from config import settings
from middleware.rate_limit import RateLimitMiddleware

from services.database import database_ping
from services.logger import logger
from services.redis_service import close_redis, get_redis
from services.rabbitmq import close_rabbitmq, get_rabbitmq, setup_rabbitmq_with_retries
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
        r = await get_redis()
        await r.ping()
        logger.debug("Redis connection is established")
        await database_ping()
        logger.debug("Database connection is established")
        await get_rabbitmq()
        logger.debug("RabbitMQ connection is established")
        await setup_rabbitmq_with_retries()
        logger.debug("RabbitMQ structure is established")
        logger.debug(
            "%s will be used as hash algorithm",
            "argon" if settings.use_argon else "bcrypt",
        )
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


def get_description():
    with open("description.md", "r", encoding="utf-8") as f:
        content = f.read()
    return content


app = FastAPI(
    title="HTTP-requester API documentation",
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
    debug=settings.debug,
    description=get_description(),
)
if os.getenv("PYTEST_RUNNING") != "1":
    app.add_middleware(RateLimitMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(router_v1)
