from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.config.environment_config import EnvironmentConfig

# Only create the Base class initially
Base = declarative_base()
ASYNC_SESSION_LOCAL = None
logger = logging.getLogger(__name__)

def init_db():
    """Initialize database connection."""
    database_url = (
        f"mysql+aiomysql://{EnvironmentConfig.get('DB_USER')}:{EnvironmentConfig.get('DB_PASSWORD')}"
        f"@{EnvironmentConfig.get('DB_HOST')}:{EnvironmentConfig.get('DB_PORT')}/{EnvironmentConfig.get('DB_NAME')}"
    )

    engine = create_async_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )

    session_maker = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )

    # we want the global session maker to be available to the entire app, its just a simpler implementation
    global ASYNC_SESSION_LOCAL # pylint: disable=global-statement
    ASYNC_SESSION_LOCAL = session_maker

    return engine, session_maker

@asynccontextmanager
async def get_db():
    """Provides a database session using the globally initialized session maker.
    This is a context manager that will yield a session to the caller.
    I am deferring transaction management to the caller. I prefer granular transaction management.
    """
    if ASYNC_SESSION_LOCAL is None:
        raise RuntimeError("Session maker is not initialized. Ensure init_db() is called during startup.")
    
    session: AsyncSession = ASYNC_SESSION_LOCAL()
    try:
        yield session
    except Exception:
        logger.exception("Error in database session, could not yield session")
        raise
    finally:
        await session.close()