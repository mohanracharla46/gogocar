"""
Pydantic schemas for Booking operations
"""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.db.models import BookingStatus, PaymentStatus


class BookingUpdate(BaseModel):
    """Schema for updating booking"""
    order_status: Optional[BookingStatus] = None
    car_id: Optional[int] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    no_of_km_travelled: Optional[float] = None
    extra_hours_charge: Optional[float] = None
    extra_km_charge: Optional[float] = None
    cancellation_reason: Optional[str] = None
    pickup_location: Optional[str] = None
    drop_location: Optional[str] = None
    delivery_address: Optional[str] = None


class BookingCancel(BaseModel):
    """Schema for cancelling booking"""
    cancellation_reason: str
    refund_amount: Optional[float] = None


class BookingResponse(BaseModel):
    """Schema for booking response"""
    id: int
    user_id: int
    car_id: int
    coupon_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    order_status: BookingStatus
    pay_advance_amount: float
    advance_amount_status: PaymentStatus
    total_amount: Optional[float] = None
    extra_hours_charge: Optional[float] = None
    extra_km_charge: Optional[float] = None
    deposit_amount: Optional[float] = None
    no_of_km_travelled: Optional[float] = None
    pickup_location: Optional[str] = None
    drop_location: Optional[str] = None
    home_delivery: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # User details
    user_firstname: Optional[str] = None
    user_lastname: Optional[str] = None
    # Car details
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    
    class Config:
        from_attributes = True


class BookingListFilter(BaseModel):
    """Schema for filtering bookings"""
    status: Optional[BookingStatus] = None
    user_id: Optional[int] = None
    car_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class MobileBookingRequest(BaseModel):
    """Schema for mobile booking request"""
    car_id: int
    start_datetime: datetime
    end_datetime: datetime


class MobileBookingResponse(BaseModel):
    """Schema for mobile booking response"""
    booking_id: int
    car_id: int
    total_price: float
    status: str
    start_datetime: datetime
    end_datetime: datetime

    class Config:
        from_attributes = True

class MobileMyBookingItem(BaseModel):
    """Schema for individual booking item in mobile 'my bookings' list"""
    booking_id: int
    car_id: int
    car_brand: str
    car_model: str
    start_datetime: datetime
    end_datetime: datetime
    total_price: float
    status: str

    class Config:
        from_attributes = True


class MobileMyBookingsResponse(BaseModel):
    """Schema for mobile 'my bookings' list response"""
    total: int
    bookings: List[MobileMyBookingItem]
