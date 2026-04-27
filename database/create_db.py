import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine
from .madels_db import Base

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


async def init_db():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")

    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()
