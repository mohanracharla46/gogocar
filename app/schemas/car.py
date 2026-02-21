"""
Pydantic schemas for Car operations
"""
from __future__ import annotations
from typing import Optional, List, Dict, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.db.models import FuelType, TransmissionType, NoOfSeats, CarType


class CarPricing(BaseModel):
    """Car pricing schema"""
    hourly: Optional[float] = None
    daily: Optional[float] = None
    weekly: Optional[float] = None
    extra_km: Optional[float] = None
    deposit: Optional[float] = None


class CarCreate(BaseModel):
    """Schema for creating a car"""
    brand: str
    car_model: str
    description: Optional[str] = None
    base_price: float
    damage_price: float
    protection_price: float
    no_of_km: int
    fuel_type: FuelType
    transmission_type: TransmissionType
    no_of_seats: NoOfSeats
    car_type: CarType
    location_id: Optional[int] = None
    maps_link: Optional[str] = None
    prices: Optional[Dict] = None
    features: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    registration_number: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    active: bool = True


class CarUpdate(BaseModel):
    """Schema for updating a car"""
    brand: Optional[str] = None
    car_model: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    damage_price: Optional[float] = None
    protection_price: Optional[float] = None
    no_of_km: Optional[int] = None
    fuel_type: Optional[FuelType] = None
    transmission_type: Optional[TransmissionType] = None
    no_of_seats: Optional[NoOfSeats] = None
    car_type: Optional[CarType] = None
    location_id: Optional[int] = None
    maps_link: Optional[str] = None
    prices: Optional[Dict] = None
    features: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    registration_number: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    active: Optional[bool] = None


class CarResponse(BaseModel):
    """Schema for car response"""
    id: int
    brand: str
    car_model: str
    description: Optional[str] = None
    base_price: float
    damage_price: float
    protection_price: float
    active: bool
    images: Optional[str] = None
    no_of_km: int
    fuel_type: FuelType
    transmission_type: TransmissionType
    no_of_seats: NoOfSeats
    car_type: CarType
    location_id: Optional[int] = None
    maps_link: Optional[str] = None
    prices: Optional[Dict] = None
    features: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    registration_number: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_validator('features', 'tags', mode='before')
    @classmethod
    def validate_json_lists(cls, v):
        """Ensure features and tags are always lists or None"""
        if v is None:
            return None
        if isinstance(v, str):
            # Try to parse as JSON string
            import json
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else None
            except:
                return None
        if isinstance(v, list):
            return v
        return None
    
    class Config:
        from_attributes = True


class CarAvailabilityCreate(BaseModel):
    """Schema for creating car availability block"""
    car_id: int
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None
    description: Optional[str] = None


class CarAvailabilityResponse(BaseModel):
    """Schema for car availability response"""
    id: int
    car_id: int
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MobileCarListing(BaseModel):
    """Schema for mobile car listing response"""
    id: int
    brand: str
    model: str
    price_per_day: float
    fuel_type: str
    transmission: str
    seats: int
    image: str

    class Config:
        from_attributes = True

class CarDetailResponse(BaseModel):
    """Schema for mobile car detail response"""
    id: int
    brand: str
    model: str
    price_per_day: float
    fuel_type: str
    transmission: str
    seats: int
    image: str
    description: Optional[str] = None
    features: Optional[List[str]] = None

    class Config:
        from_attributes = True
