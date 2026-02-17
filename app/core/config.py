"""
Application configuration and settings management
"""
import os
from typing import Optional
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "GoGoCar"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./gogocar.db"
    ).replace("postgres://", "postgresql://", 1)
    
    # Authentication
    LOGIN_URL: str = "/auth/login"
    SIGNUP_URL: str = "/auth/signup"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "7b63e8a4f8d9b0c1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5")
    
    # AWS S3
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "gogocar")
    
    # CCAvenue Payment Gateway
    CCAVENUE_MERCHANT_ID: str = os.getenv("CCAVENUE_MERCHANT_ID", "")
    CCAVENUE_ACCESS_CODE: str = os.getenv("CCAVENUE_ACCESS_CODE", "")
    CCAVENUE_WORKING_KEY: str = os.getenv("CCAVENUE_WORKING_KEY", "")
    CCAVENUE_ENVIRONMENT: str = os.getenv("CCAVENUE_ENVIRONMENT", "test")  # test or production
    CCAVENUE_REDIRECT_URL: str = os.getenv(
        "CCAVENUE_REDIRECT_URL",
        "http://localhost:8000/payments/callback"
    )
    CCAVENUE_CANCEL_URL: str = os.getenv(
        "CCAVENUE_CANCEL_URL",
        "http://localhost:8000/payments/cancel"
    )
    DOMAIN_URL: str = os.getenv("DOMAIN_URL", "http://localhost:8000")
    
    # File Upload
    IMAGE_DIR: str = "static/images/"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # AWS SES (Email)
    SES_REGION: str = os.getenv("SES_REGION", "us-east-1")
    SES_FROM_EMAIL: str = os.getenv("SES_FROM_EMAIL", "no-reply@gogocar.in")
    SES_FROM_NAME: str = os.getenv("SES_FROM_NAME", "GoGoCar")
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance with placeholder filtering"""
    s = Settings()
    # Filter out common placeholders from environment
    placeholders = ["XXXX", "your-", "replace-"]
    
    def is_placeholder(val: Optional[str]) -> bool:
        if not val: return True
        return any(p in val for p in placeholders) or any(p in val.lower() for p in placeholders)

    if is_placeholder(s.AWS_ACCESS_KEY_ID):
        s.AWS_ACCESS_KEY_ID = None
    if is_placeholder(s.AWS_SECRET_ACCESS_KEY):
        s.AWS_SECRET_ACCESS_KEY = None
        
    return s


# Global settings instance
settings = get_settings()

