"""
Pydantic schemas for Support Ticket operations
"""
from __future__ import annotations
from typing import Optional, Union
from datetime import datetime
from pydantic import BaseModel, field_validator

from app.db.models import TicketStatus


class TicketCreate(BaseModel):
    """Schema for creating support ticket"""
    subject: str
    description: str
    order_id: Optional[int] = None
    priority: str = "MEDIUM"


class TicketUpdate(BaseModel):
    """Schema for updating support ticket"""
    status: Optional[TicketStatus] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None
    resolution_notes: Optional[str] = None
    
    @field_validator('status', mode='before')
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return TicketStatus(v.upper())
            except ValueError:
                raise ValueError(f"Invalid status: {v}. Must be one of: {[s.value for s in TicketStatus]}")
        return v


class TicketResponse(BaseModel):
    """Schema for ticket response"""
    id: int
    ticket_number: str
    user_id: Optional[int] = None
    order_id: Optional[int] = None
    subject: str
    description: str
    status: TicketStatus
    priority: str
    assigned_to: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    # User details (optional, populated when needed)
    user_firstname: Optional[str] = None
    user_lastname: Optional[str] = None
    
    class Config:
        from_attributes = True

