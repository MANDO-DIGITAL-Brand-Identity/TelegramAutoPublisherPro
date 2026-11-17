"""
Database connection and initialization for Telegram Auto Publisher Pro
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event

from config import config

# Import Base from models
from .models import Base

logger = logging.getLogger(__name__)


# Create async engines
async_engine: AsyncEngine = create_async_engine(
    config.database.database_url,
    echo=config.DEBUG,
    future=True,
)

# For sync operations (migrations)
engine = None
if config.database.DB_TYPE == "sqlite":
    # For SQLite, we can use the same async engine for sync operations
    # But for migrations, we need a sync engine
    from sqlalchemy import create_engine as create_sync_engine
    engine = create_sync_engine(
        config.database.database_url.replace("sqlite+aiosqlite:///", "sqlite:///"),
        echo=config.DEBUG,
    )
else:
    # For PostgreSQL, create a sync engine
    from sqlalchemy import create_engine as create_sync_engine
    engine = create_sync_engine(
        config.database.database_url.replace("postgresql+asyncpg://", "postgresql://"),
        echo=config.DEBUG,
    )


# Create async session factory
async_session_maker = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional scope around a series of operations.
    This ensures that the session is properly closed after use.
    """
    session: AsyncSession = async_session_maker()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


async def init_db():
    """
    Initialize the database by creating all tables.
    This should be called once during application startup.
    """
    logger.info("Initializing database...")
    
    try:
        async with async_engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
        
        # For SQLite, also create with sync engine for migrations
        if config.database.DB_TYPE == "sqlite" and engine:
            Base.metadata.create_all(engine)
        
        logger.info("Database initialization completed")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_db():
    """
    Close all database connections.
    This should be called during application shutdown.
    """
    logger.info("Closing database connections...")
    
    try:
        await async_engine.dispose()
        if engine:
            engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise


async def check_db_connection() -> bool:
    """
    Check if the database connection is working.
    """
    try:
        async with async_engine.begin() as conn:
            # Execute a simple query to test the connection
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def get_db_stats() -> dict:
    """
    Get database statistics.
    """
    stats = {
        "db_type": config.database.DB_TYPE,
        "tables": [],
        "row_counts": {},
    }
    
    try:
        async with async_engine.begin() as conn:
            # Get list of tables
            if config.database.DB_TYPE == "sqlite":
                result = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = [row[0] for row in result.fetchall()]
            else:
                result = await conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )
                tables = [row[0] for row in result.fetchall()]
            
            stats["tables"] = tables
            
            # Get row counts for each table
            for table in tables:
                try:
                    result = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = result.scalar()
                    stats["row_counts"][table] = count
                except Exception as e:
                    logger.warning(f"Could not count rows for table {table}: {e}")
                    stats["row_counts"][table] = "error"
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
    
    return stats


# For backward compatibility and testing
sync_session_maker = None
if engine:
    from sqlalchemy.orm import sessionmaker as sync_sessionmaker
    sync_session_maker = sync_sessionmaker(bind=engine)


__all__ = [
    "async_engine",
    "engine",
    "async_session_maker",
    "get_async_session",
    "init_db",
    "close_db",
    "check_db_connection",
    "get_db_stats",
    "Base",
]
