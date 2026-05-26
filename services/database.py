from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings
import ssl

postgres_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.postgres_user,
    password=settings.postgres_password,
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_database,
)
connect_args = {}
if settings.postgres_use_ssl and settings.postgres_ca_cert:
    ssl_ctx = ssl.create_default_context(cafile=settings.postgres_ca_cert)
    if settings.postgres_cert and settings.postgres_key:
        ssl_ctx.load_cert_chain(certfile=settings.postgres_cert, keyfile=settings.postgres_key)
    connect_args = {"ssl": ssl_ctx}

engine = create_async_engine(
    postgres_url,
    pool_pre_ping=True,
    echo=True,
    future=True,
    connect_args=connect_args if connect_args else None,
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