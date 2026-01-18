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
        "postgresql+psycopg2://postgres:postgres@localhost:5432/gogocar"
    )
    
    # AWS Cognito
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    USERPOOL_ID: str = os.getenv("USERPOOL_ID", "")
    APP_CLIENT_ID: str = os.getenv("APP_CLIENT_ID", "")
    APP_CLIENT_SECRET: str = os.getenv("APP_CLIENT_SECRET", "")
    COGNITO_DOMAIN: str = os.getenv("COGNITO_DOMAIN", "")
    REDIRECT_URI: str = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/token")
    LOGIN_URL: str = os.getenv("LOGIN_URL", "")
    
    # AWS S3
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
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "production key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()

