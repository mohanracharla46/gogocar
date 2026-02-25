"""
Pydantic schemas for all Mobile API endpoints.
Kept separate from web schemas to avoid coupling.
"""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.db.models import KYCStatus


# ─────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────

class MobileProfileResponse(BaseModel):
    """Response schema for GET /api/mobile/profile"""
    id: int
    username: str
    firstname: str
    lastname: str
    email: str
    phone: Optional[str] = None
    permanentaddress: Optional[str] = None
    kyc_status: str
    created_at: Optional[datetime] = None
    aadhaar_front: Optional[str]
    aadhaar_back: Optional[str]
    drivinglicense_front: Optional[str]
    drivinglicense_back: Optional[str]

    class Config:
        from_attributes = True


class MobileProfileUpdate(BaseModel):
    """Request schema for PUT /api/mobile/profile"""
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    phone: Optional[str] = None
    permanentaddress: Optional[str] = None


class MobileChangePasswordRequest(BaseModel):
    """Request schema for PUT /api/mobile/change-password"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class MobileMessageResponse(BaseModel):
    """Generic message response"""
    message: str


# ─────────────────────────────────────────────
# KYC
# ─────────────────────────────────────────────

class MobileKYCUploadResponse(BaseModel):
    """Response schema for POST /api/mobile/kyc/upload"""
    success: bool
    kyc_status: str


class MobileKYCStatusResponse(BaseModel):
    """Response schema for GET /api/mobile/kyc/status"""
    kyc_status: str
    reason: Optional[str] = None


# ─────────────────────────────────────────────
# Booking – Calculate
# ─────────────────────────────────────────────

class MobileBookingCalculateRequest(BaseModel):
    """Request schema for POST /api/bookings/calculate"""
    car_id: int
    pickup_datetime: datetime
    return_datetime: datetime
    damage_protection: Optional[float] = Field(0.0, ge=0)


class MobileBookingCalculateResponse(BaseModel):
    """Response schema for POST /api/bookings/calculate"""
    days: int
    base_price: float
    damage_protection: float
    security_deposit: float
    total: float


# ─────────────────────────────────────────────
# Booking – Detail
# ─────────────────────────────────────────────

class MobileBookingDetailResponse(BaseModel):
    """Response schema for GET /api/bookings/{booking_id}"""
    booking_id: int
    car_id: int
    car_brand: str
    car_model: str
    start_datetime: datetime
    end_datetime: datetime
    status: str
    total_price: float
    cancellation_reason: Optional[str] = None
    created_at: Optional[datetime] = None


# ─────────────────────────────────────────────
# Booking – Cancel
# ─────────────────────────────────────────────

class MobileBookingCancelResponse(BaseModel):
    """Response schema for POST /api/bookings/{booking_id}/cancel"""
    booking_id: int
    status: str
    message: str


# ─────────────────────────────────────────────
# Payment – Initiate
# ─────────────────────────────────────────────

class MobilePaymentInitiateRequest(BaseModel):
    """Request schema for POST /api/payments/initiate"""
    booking_id: int


class MobilePaymentInitiateResponse(BaseModel):
    """Response schema for POST /api/payments/initiate"""
    booking_id: int
    payment_id: int
    amount: float


# ─────────────────────────────────────────────
# Payment – Verify
# ─────────────────────────────────────────────

class MobilePaymentVerifyRequest(BaseModel):
    """Request schema for POST /api/payments/verify"""
    payment_id: int
    status: str  # SUCCESS or FAILED
    transaction_id: Optional[str] = None


class MobilePaymentVerifyResponse(BaseModel):
    """Response schema for POST /api/payments/verify"""
    success: bool
    booking_status: str
