from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings

import os
from sqlalchemy.pool import NullPool

# Async Engine for FastAPI endpoints
if "sqlite" in settings.DATABASE_URL or os.getenv("TESTING", "").lower() == "true":
    async_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool
    )
else:
    async_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        pool_size=20,
        max_overflow=10
    )

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Synchronous Engine for Alembic migrations and Seed Data scripts
if "sqlite" in settings.SYNC_DATABASE_URL:
    sync_engine = create_engine(
        settings.SYNC_DATABASE_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False}
    )
else:
    sync_engine = create_engine(
        settings.SYNC_DATABASE_URL,
        echo=False,
        future=True
    )

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
