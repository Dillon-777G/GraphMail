import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv


if not load_dotenv():
    raise FileNotFoundError("Error: .env file not found or failed to load.")


def is_running_in_docker():
    try:
        with open("/proc/1/cgroup", "rt", encoding="utf-8") as f:
            return "docker" in f.read()
    except FileNotFoundError:
        return False

# Default to local development settings if not set
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD") 
DB_HOST = os.getenv("DB_HOST_DOCKER") if is_running_in_docker() else os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Update URL to use async driver
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,  # Default connection pool size
    max_overflow=10,  # Allow up to 10 connections beyond pool_size
    pool_timeout=30,  # Seconds to wait before timing out on getting a connection
    pool_recycle=1800,  # Recycle connections after 30 minutes to handle stale connections
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

@asynccontextmanager
async def get_db():
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()