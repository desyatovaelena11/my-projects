"""
Подключение к базе данных PostgreSQL (Supabase).

SQLAlchemy — это инструмент, который позволяет работать с базой данных
на Python, не писать голый SQL вручную.

asyncpg — быстрый асинхронный драйвер для PostgreSQL.
Асинхронный значит: пока ждём ответа от базы, сервер может обрабатывать
другие запросы — не зависает.
"""

import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

# asyncpg требует схему "postgresql+asyncpg://" вместо "postgresql://"
_raw_url = os.environ["DATABASE_URL"]
DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# engine — это само "соединение" с базой данных
engine = create_async_engine(DATABASE_URL, echo=False)

# SessionLocal — фабрика сессий. Сессия = один разговор с базой данных.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей (описаний таблиц)."""
    pass


async def get_db() -> AsyncSession:
    """
    Зависимость FastAPI: открывает сессию для каждого запроса,
    автоматически закрывает после ответа.
    """
    async with SessionLocal() as session:
        yield session
