"""
Pydantic schemas for User operations
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.db.models import KYCStatus


class UserUpdate(BaseModel):
    """Schema for updating user"""
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    permanentaddress: Optional[str] = None
    is_active: Optional[bool] = None
    kyc_status: Optional[KYCStatus] = None
    aadhaar_front: Optional[str] = None
    aadhaar_back: Optional[str] = None
    drivinglicense_front: Optional[str] = None
    drivinglicense_back: Optional[str] = None
    kyc_rejection_reason: Optional[str] = None


class KYCApprove(BaseModel):
    """Schema for approving KYC"""
    pass  # No additional fields needed


class KYCReject(BaseModel):
    """Schema for rejecting KYC"""
    rejection_reason: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    firstname: str
    lastname: str
    email: str
    isadmin: bool
    is_active: bool
    phone: Optional[str] = None
    permanentaddress: Optional[str] = None
    kyc_status: KYCStatus
    kyc_approved_at: Optional[datetime] = None
    kyc_approved_by: Optional[int] = None
    kyc_rejection_reason: Optional[str] = None
    aadhaar_front: Optional[str] = None
    aadhaar_back: Optional[str] = None
    drivinglicense_front: Optional[str] = None
    drivinglicense_back: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class KYCDocumentUpload(BaseModel):
    """Schema for KYC document upload response"""
    document_type: str  # aadhaar_front, aadhaar_back, dl_front, dl_back
    file_url: str
    uploaded_at: datetime

