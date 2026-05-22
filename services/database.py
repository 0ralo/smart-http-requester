from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings

password_part = f":{settings.postgres_password}" if settings.postgres_password else ""
engine = create_async_engine(
    f"postgresql+psycopg://{settings.postgres_user}{password_part}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}",
    pool_pre_ping=True,
    echo=True,
    future=True
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