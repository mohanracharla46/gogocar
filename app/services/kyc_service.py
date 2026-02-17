"""
KYC service for handling user KYC document uploads and verification
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.db.models import UserProfile
from app.core.logging_config import logger
from app.utils.s3_service import s3_service


class KYCService:
    """Service for KYC document management"""
    
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    
    @staticmethod
    def validate_file(file) -> bool:
        """
        Validate uploaded file
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            True if valid, False otherwise
        """
        if not file.filename:
            return False
        
        # Check file extension
        from pathlib import Path
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in KYCService.ALLOWED_EXTENSIONS:
            return False
        
        # File size will be checked during upload
        return True
    
    @staticmethod
    async def upload_kyc_document(
        db: Session,
        user_id: int,
        document_type: str,
        file
    ) -> Optional[str]:
        """
        Upload KYC document to S3 and update user profile
        
        Args:
            db: Database session
            user_id: User ID
            document_type: Type of document (aadhaar_front, aadhaar_back, dl_front, dl_back)
            file: FastAPI UploadFile object
            
        Returns:
            S3 URL of uploaded document or None
        """
        try:
            # Validate document type
            valid_types = ['aadhaar_front', 'aadhaar_back', 'dl_front', 'dl_back']
            if document_type not in valid_types:
                logger.error(f"Invalid document type: {document_type}")
                return None
            
            # Validate file
            if not KYCService.validate_file(file):
                logger.error(f"Invalid file format for {document_type}")
                return None
            
            # Get user profile first
            # Check file size using the .size attribute available in modern FastAPI/Starlette
            file_size = file.size if hasattr(file, 'size') else 0
            
            if file_size > KYCService.MAX_FILE_SIZE:
                logger.error(f"File too large: {file_size} bytes")
                return None

            user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
            if not user:
                logger.error(f"User not found: {user_id}")
                return None
            
            # Upload to S3
            s3_url = await s3_service.upload_kyc_document(file, user_id, document_type)
            
            # Map document_type to model field
            if document_type == 'aadhaar_front':
                user.aadhaar_front = s3_url
            elif document_type == 'aadhaar_back':
                user.aadhaar_back = s3_url
            elif document_type == 'dl_front':
                user.drivinglicense_front = s3_url
            elif document_type == 'dl_back':
                user.drivinglicense_back = s3_url
            
            # Update KYC status if all documents are uploaded
            if (user.aadhaar_front and user.aadhaar_back and 
                user.drivinglicense_front and user.drivinglicense_back):
                from app.db.models import KYCStatus
                current_status = user.kyc_status
                if hasattr(current_status, 'value'):
                    current_status = current_status.value
                
                if current_status == 'NOT_SUBMITTED':
                    user.kyc_status = KYCStatus.PENDING
            
            db.commit()
            db.refresh(user)
            
            logger.info(f"KYC document uploaded for user {user_id}: {document_type}")
            return s3_url
            
        except Exception as e:
            logger.error(f"Error uploading KYC document: {str(e)}")
            db.rollback()
            return None
    
    @staticmethod
    def get_missing_documents(user: UserProfile) -> List[str]:
        """
        Get list of missing KYC documents
        
        Args:
            user: UserProfile object
            
        Returns:
            List of missing document types
        """
        missing = []
        
        if not user.aadhaar_front:
            missing.append('aadhaar_front')
        if not user.aadhaar_back:
            missing.append('aadhaar_back')
        if not user.drivinglicense_front:
            missing.append('dl_front')
        if not user.drivinglicense_back:
            missing.append('dl_back')
        
        return missing
    
    @staticmethod
    def is_kyc_complete(user: UserProfile) -> bool:
        """
        Check if user has all KYC documents uploaded
        
        Args:
            user: UserProfile object
            
        Returns:
            True if all documents are uploaded, False otherwise
        """
        missing = KYCService.get_missing_documents(user)
        return len(missing) == 0


# Global instance
kyc_service = KYCService()

