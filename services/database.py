from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings
from services.logger import logger

postgres_url = URL.create(
    drivername="postgresql+asyncpg",
    username=settings.postgres_user,
    password=settings.postgres_password,
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_database,
)

engine = create_async_engine(
    postgres_url,
    pool_pre_ping=True,
    echo=True,
    future=True,
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False
)


async def database_ping() -> bool:
    logger.debug("Pinging database")
    try:
        async with async_session() as session:
            query = await session.execute(text(
                """select 1"""
            ))
            result = query.scalar_one() == 1
            logger.debug("Database ping successful")
            return result
    except Exception:
        logger.exception("Database ping failed")
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    logger.debug("Opening database session")
    async with async_session() as session:
        try:
            yield session
            await session.commit()
            logger.debug("Database session committed")
        except Exception:
            await session.rollback()
            logger.exception("Database session rollback due to error")
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")