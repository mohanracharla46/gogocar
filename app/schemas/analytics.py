"""
Pydantic schemas for Analytics/Dashboard
"""
from __future__ import annotations
from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel


class BookingSummary(BaseModel):
    """Booking summary"""
    total: int
    pending: int
    approved: int
    booked: int
    ongoing: int
    completed: int
    cancelled: int


class RevenueSummary(BaseModel):
    """Revenue summary"""
    total_revenue: float
    advance_collected: float
    balance_pending: float
    deposits_held: float
    refunds_processed: float
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class CarPerformance(BaseModel):
    """Car performance metrics"""
    car_id: int
    car_name: str
    total_bookings: int
    total_revenue: float
    average_rating: Optional[float] = None
    utilization_rate: Optional[float] = None


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    bookings_summary: BookingSummary
    revenue_summary: RevenueSummary
    cars_currently_rented: int
    top_performing_cars: List[CarPerformance]
    least_performing_cars: List[CarPerformance]
    user_growth: Dict[str, int]  # {period: count}
    category_performance: Dict[str, Dict]  # {category: {bookings, revenue}}
    booking_timeseries: Optional[Dict[str, int]] = None  # {date: count}
    revenue_timeseries: Optional[Dict[str, float]] = None  # {date: revenue}

