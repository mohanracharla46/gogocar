"""
Pydantic schemas for Review operations
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    """Schema for creating a review"""
    order_id: int
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    review_text: Optional[str] = None


class ReviewUpdate(BaseModel):
    """Schema for updating review visibility"""
    is_approved: Optional[bool] = None
    is_hidden: Optional[bool] = None


class ReviewResponse(BaseModel):
    """Schema for review response"""
    id: int
    car_id: int
    user_id: int
    order_id: Optional[int] = None
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None
    is_approved: bool
    is_hidden: bool
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # User details (optional, populated when needed)
    user_firstname: Optional[str] = None
    user_lastname: Optional[str] = None
    # Car details (optional)
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    
    class Config:
        from_attributes = True

