"""
Async database connection management using SQLAlchemy with asyncpg.
"""
import logging
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from typing import AsyncGenerator
from sqlalchemy import text
from config.settings import settings

logger = logging.getLogger(__name__)

# Lazy-loaded engine and session factory
_engine = None
_async_session_factory = None


async def init_db() -> None:
    """Initialize database engine and session factory."""
    global _engine, _async_session_factory
    
    # Create async engine
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,  # Test connections before using
        future=True, 
    )
    
    # Create async session factory
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    logger.info("Database engine initialized successfully")


async def close_db() -> None:
    """Close database engine."""
    global _engine
    
    if _engine:
        await _engine.dispose()
        logger.info("Database engine closed")


def get_session_factory():
    """Get the async session factory."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session

class Database:
    """Database operations helper."""
    
    @staticmethod
    async def create_tables() -> None:
        """Create all tables in database."""
        from app.db.models import Base
        
        if _engine is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    @staticmethod
    async def drop_tables() -> None:
        """Drop all tables in database (use with caution)."""
        from app.db.models import Base
        
        if _engine is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")
    
    @staticmethod
    async def health_check() -> bool:
        """Check database connection health."""
        try:
            if _engine is None:
                return False
            
            async with _engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
