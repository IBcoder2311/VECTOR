from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy.orm import DeclarativeBase
from core.config import Config

config = Config()

DATABASE_URL = config.create_url_db()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_session():
    async with SessionFactory() as session:
        yield session

async def create_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

async def close_database():
    await engine.dispose()

