from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DATABASE

engine = create_async_engine(
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DATABASE}",
    pool_pre_ping=True,
    echo=True
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False
)


async def database_ping() -> bool:
    async with async_session() as session:
        query = await session.execute(text(
            """select 1"""
        ))
        return query.scalar_one() == 1


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()