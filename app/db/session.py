"""
Database session management
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
from app.core.logging_config import logger

# Create database engine
# Create database engine
connect_args = {}
engine_args = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG
}

if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False
else:
    engine_args["pool_size"] = 10
    engine_args["max_overflow"] = 20

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_args
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        # Ensure rollback if commit failed and session is still active
        try:
            if db.is_active:
                db.rollback()
        except Exception:
            pass
        db.close()


def init_db() -> None:
    """Initialize database tables"""
    try:
        # Import all models to register them
        from app.db import models  # noqa: F401
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

