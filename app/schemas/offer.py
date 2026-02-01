"""
Pydantic schemas for Offer/Coupon operations
"""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class OfferCreate(BaseModel):
    """Schema for creating an offer"""
    coupon_code: str
    discount: int
    discount_type: str = "PERCENTAGE"  # PERCENTAGE or FIXED
    expiration_time: datetime
    usage_limit: Optional[int] = None
    min_amount: Optional[float] = None
    max_discount: Optional[float] = None
    applicable_to_car_type: Optional[List[str]] = None
    applicable_to_car_ids: Optional[List[int]] = None
    description: Optional[str] = None
    is_active: bool = True


class OfferUpdate(BaseModel):
    """Schema for updating an offer"""
    coupon_code: Optional[str] = None
    discount: Optional[int] = None
    discount_type: Optional[str] = None
    expiration_time: Optional[datetime] = None
    usage_limit: Optional[int] = None
    min_amount: Optional[float] = None
    max_discount: Optional[float] = None
    applicable_to_car_type: Optional[List[str]] = None
    applicable_to_car_ids: Optional[List[int]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OfferResponse(BaseModel):
    """Schema for offer response"""
    id: int
    coupon_code: str
    discount: int
    discount_type: str
    is_active: bool
    expiration_time: datetime
    usage_limit: Optional[int] = None
    usage_count: int
    min_amount: Optional[float] = None
    max_discount: Optional[float] = None
    applicable_to_car_type: Optional[List[str]] = None
    applicable_to_car_ids: Optional[List[int]] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

