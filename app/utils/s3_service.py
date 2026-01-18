"""
S3 service for file uploads and management
"""
from typing import Optional, List
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
import uuid
import os
from datetime import datetime

from app.core.config import settings
from app.core.logging_config import logger


class S3Service:
    """Service for S3 file operations"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION
    
    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "uploads",
        object_name: Optional[str] = None
    ) -> str:
        """
        Upload a file to S3
        
        Args:
            file: FastAPI UploadFile object
            folder: S3 folder/prefix
            object_name: Optional custom object name
            
        Returns:
            S3 URL of uploaded file
        """
        try:
            # Generate unique object name if not provided
            if not object_name:
                file_extension = Path(file.filename).suffix if file.filename else '.bin'
                object_name = f"{folder}/{uuid.uuid4().hex}{file_extension}"
            
            # Ensure folder prefix
            if not object_name.startswith(folder):
                object_name = f"{folder}/{object_name}"
            
            # Read file content into memory to avoid file pointer issues
            # Reset file pointer first
            await file.seek(0)
            file_content = await file.read()
            await file.seek(0)  # Reset again for potential reuse
            
            # Upload from bytes
            from io import BytesIO
            file_obj = BytesIO(file_content)
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_name,
                ExtraArgs={'ContentType': file.content_type}
            )
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_name}"
            
            logger.info(f"File uploaded to S3: {url}")
            return url
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {str(e)}")
            raise
    
    async def upload_multiple_files(
        self,
        files: List[UploadFile],
        folder: str = "uploads"
    ) -> List[str]:
        """
        Upload multiple files to S3
        
        Args:
            files: List of FastAPI UploadFile objects
            folder: S3 folder/prefix
            
        Returns:
            List of S3 URLs
        """
        urls = []
        for file in files:
            try:
                url = await self.upload_file(file, folder)
                urls.append(url)
            except Exception as e:
                logger.error(f"Error uploading file {file.filename}: {str(e)}")
                # Continue with other files
                continue
        return urls
    
    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from S3
        
        Args:
            object_name: S3 object key/name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            logger.info(f"File deleted from S3: {object_name}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting file: {str(e)}")
            return False
    
    async def upload_car_image(
        self,
        file: UploadFile,
        car_id: int
    ) -> str:
        """
        Upload car image to S3 with organized structure
        
        Args:
            file: FastAPI UploadFile object
            car_id: Car ID
            
        Returns:
            S3 URL of uploaded image
        """
        folder = f"cars/{car_id}/images"
        return await self.upload_file(file, folder)
    
    async def upload_kyc_document(
        self,
        file: UploadFile,
        user_id: int,
        document_type: str  # aadhaar_front, aadhaar_back, dl_front, dl_back
    ) -> str:
        """
        Upload KYC document to S3
        
        Args:
            file: FastAPI UploadFile object
            user_id: User ID
            document_type: Type of document
            
        Returns:
            S3 URL of uploaded document
        """
        folder = f"users/{user_id}/kyc/{document_type}"
        return await self.upload_file(file, folder)
    
    async def upload_maintenance_photo(
        self,
        file: UploadFile,
        maintenance_id: int
    ) -> str:
        """
        Upload maintenance photo to S3
        
        Args:
            file: FastAPI UploadFile object
            maintenance_id: Maintenance log ID
            
        Returns:
            S3 URL of uploaded photo
        """
        folder = f"maintenance/{maintenance_id}/photos"
        return await self.upload_file(file, folder)
    
    async def upload_damage_photo(
        self,
        file: UploadFile,
        damage_report_id: int
    ) -> str:
        """
        Upload damage report photo to S3
        
        Args:
            file: FastAPI UploadFile object
            damage_report_id: Damage report ID
            
        Returns:
            S3 URL of uploaded photo
        """
        folder = f"damage/{damage_report_id}/photos"
        return await self.upload_file(file, folder)


# Global instance
s3_service = S3Service()

