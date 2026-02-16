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
        from app.db import models
        Base.metadata.create_all(bind=engine)
        
        # Check if hashed_password column exists (manual migration)
        db = SessionLocal()
        try:
            from sqlalchemy import text
            # Very basic check for hashed_password column
            if "sqlite" in settings.DATABASE_URL:
                db.execute(text("ALTER TABLE user_profiles ADD COLUMN hashed_password VARCHAR"))
                db.commit()
                logger.info("Added hashed_password column to user_profiles")
        except Exception:
            # Column likely already exists
            db.rollback()
        
        # Create default admin if not exists, or update if hashed_password is NULL
        from app.core.security import get_password_hash
        admin = db.query(models.UserProfile).filter(models.UserProfile.username == "admin").first()
        if not admin:
            admin = models.UserProfile(
                username="admin",
                email="admin@gogocar.in",
                firstname="Admin",
                lastname="User",
                hashed_password=get_password_hash("admin123"),
                isadmin=True,
                is_active=True,
                kyc_status=models.KYCStatus.NOT_SUBMITTED
            )
            db.add(admin)
            logger.info("Default admin user created (admin/admin123)")
        elif admin.hashed_password is None:
            admin.hashed_password = get_password_hash("admin123")
            admin.kyc_status = models.KYCStatus.NOT_SUBMITTED
            logger.info("Updated existing admin user with hashed password")
        
        db.commit()
        db.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

