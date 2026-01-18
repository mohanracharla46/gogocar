"""
Legacy file utilities for S3 upload (deprecated - use s3_service instead)
Kept for backward compatibility
"""
from typing import Optional
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.logging_config import logger

# Import new S3 service for reuse
from app.utils.s3_service import s3_service


def upload_file_to_s3(
    filepath: str,
    bucket_name: str,
    object_name: Optional[str] = None
) -> str:
    """
    Upload a file to S3 bucket (legacy function - use s3_service instead)
    
    Args:
        filepath: Local file path (relative or absolute)
        bucket_name: S3 bucket name
        object_name: S3 object name (optional)
        
    Returns:
        S3 URL of uploaded file
    """
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # Resolve filepath (handle relative paths)
        file_path = Path(filepath)
        if not file_path.is_absolute():
            # If relative, make it relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            file_path = project_root / filepath
        
        if object_name is None:
            object_name = file_path.name
        
        s3_client.upload_file(str(file_path), bucket_name, object_name)
        
        # Generate URL
        url = f"https://{bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{object_name}"
        
        logger.info(f"File uploaded to S3: {url}")
        return url
        
    except ClientError as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading file: {str(e)}")
        raise

