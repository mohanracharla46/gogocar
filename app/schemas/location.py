"""
Pydantic schemas for Location operations
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class LocationCreate(BaseModel):
    """Schema for creating a location"""
    location: str
    maps_link: Optional[str] = None


class LocationUpdate(BaseModel):
    """Schema for updating a location"""
    location: Optional[str] = None
    maps_link: Optional[str] = None


class LocationResponse(BaseModel):
    """Schema for location response"""
    id: int
    location: str
    maps_link: Optional[str] = None
    
    class Config:
        from_attributes = True

