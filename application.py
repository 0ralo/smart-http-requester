from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger
from api.v1 import router as router_v1


@asynccontextmanager
async def lifespan(_: FastAPI):
    # before start
    await pre_check()
    # server is online
    yield
    # before shutdown
    await pre_shutdown()


async def pre_check():
    logger.add("logs/app.log", rotation="monthly")
    logger.info("Server is starting")


async def pre_shutdown():
    logger.info("Server is shutting down")


app = FastAPI(
    title="HTTP-requester API documentation",
    lifespan=lifespan,
    openapi_url="/api/openapi.json"

)
app.include_router(router_v1)
