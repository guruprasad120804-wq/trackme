from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Neon requires SSL; use smaller pool for free tier
connect_args = {}
db_url = settings.database_url
if "neon.tech" in db_url:
    connect_args["ssl"] = True
    # asyncpg doesn't understand sslmode — strip it from the URL
    import re
    db_url = re.sub(r"[?&]sslmode=[^&]*", "", db_url)
    # Clean up dangling ? if sslmode was the only param
    db_url = db_url.rstrip("?")

engine = create_async_engine(
    db_url,
    echo=False,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    connect_args=connect_args,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
