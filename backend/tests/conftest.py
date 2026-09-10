import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest_asyncio
from app.core.database import async_engine, Base, AsyncSessionLocal
from sqlalchemy import select, func
from app.models.user import User

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        user_count = await session.scalar(select(func.count(User.id)))
        if not user_count or user_count == 0:
            from seed.seed_data import run_seed
            run_seed()
    yield
