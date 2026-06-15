from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger
from api.v1 import router as router_v1
from config import settings

from services.database import database_ping
from services.redis import close_redis, get_redis
from services.rabbitmq import close_rabbitmq, get_rabbitmq, ensure_structure
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
    logger.add("logs/app.log", rotation="monthly", retention="3 month", compression="gz")
    logger.info("Server is starting")
    await (await get_redis()).ping()
    logger.debug("Redis connection is established")
    await database_ping()
    logger.debug("Database connection is established")
    await get_rabbitmq()
    logger.debug("RabbitMQ connection is established")
    await ensure_structure()
    logger.debug("RabbitMQ structure is established")


async def pre_shutdown():
    logger.info("Server is shutting down")
    await close_rabbitmq()
    await close_redis()


app = FastAPI(
    title="HTTP-requester API documentation",
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
    debug=settings.debug,
)

# Add metrics middleware to collect HTTP metrics
app.add_middleware(MetricsMiddleware)

app.include_router(router_v1)
