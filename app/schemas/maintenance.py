"""
Pydantic schemas for Maintenance operations
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.db.models import MaintenanceType


class MaintenanceCreate(BaseModel):
    """Schema for creating maintenance log"""
    car_id: int
    maintenance_type: MaintenanceType
    title: str
    description: Optional[str] = None
    cost: Optional[float] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    service_provider: Optional[str] = None


class MaintenanceUpdate(BaseModel):
    """Schema for updating maintenance log"""
    maintenance_type: Optional[MaintenanceType] = None
    title: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    service_provider: Optional[str] = None


class MaintenanceResponse(BaseModel):
    """Schema for maintenance response"""
    id: int
    car_id: int
    maintenance_type: MaintenanceType
    title: str
    description: Optional[str] = None
    cost: Optional[float] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    service_provider: Optional[str] = None
    photos: Optional[str] = None
    created_at: Optional[datetime] = None
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    car_registration: Optional[str] = None
    
    class Config:
        from_attributes = True


class DamageReportCreate(BaseModel):
    """Schema for creating damage report"""
    car_id: int
    order_id: Optional[int] = None
    damage_description: str
    repair_cost: Optional[float] = None


class DamageReportUpdate(BaseModel):
    """Schema for updating damage report"""
    damage_description: Optional[str] = None
    repair_cost: Optional[float] = None
    repair_status: Optional[str] = None


class DamageReportResponse(BaseModel):
    """Schema for damage report response"""
    id: int
    car_id: int
    order_id: Optional[int] = None
    damage_description: str
    damage_photos: Optional[str] = None
    repair_cost: Optional[float] = None
    repair_status: str
    repaired_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    car_registration: Optional[str] = None
    order_reference: Optional[str] = None
    
    class Config:
        from_attributes = True

