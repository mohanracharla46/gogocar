"""
Analytics service for dashboard statistics
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.db.models import Orders, Cars, UserProfile, BookingStatus, PaymentStatus
from app.db.models import PaymentLog, Ratings
from app.schemas.analytics import (
    BookingSummary, RevenueSummary, CarPerformance, DashboardStats
)
from app.core.logging_config import logger


class AnalyticsService:
    """Service for analytics and dashboard data"""
    
    @staticmethod
    def get_booking_summary(db: Session) -> BookingSummary:
        """Get booking summary statistics"""
        total = db.query(func.count(Orders.id)).scalar() or 0
        pending = db.query(func.count(Orders.id)).filter(
            Orders.order_status == BookingStatus.PENDING
        ).scalar() or 0
        approved = db.query(func.count(Orders.id)).filter(
            Orders.order_status == BookingStatus.APPROVED
        ).scalar() or 0
        booked = db.query(func.count(Orders.id)).filter(
            Orders.order_status == BookingStatus.BOOKED
        ).scalar() or 0
        ongoing = db.query(func.count(Orders.id)).filter(
            Orders.order_status == BookingStatus.ONGOING
        ).scalar() or 0
        completed = db.query(func.count(Orders.id)).filter(
            Orders.order_status == BookingStatus.COMPLETED
        ).scalar() or 0
        cancelled = db.query(func.count(Orders.id)).filter(
            Orders.order_status == BookingStatus.CANCELLED
        ).scalar() or 0
        
        return BookingSummary(
            total=total,
            pending=pending,
            approved=approved,
            booked=booked,
            ongoing=ongoing,
            completed=completed,
            cancelled=cancelled
        )
    
    @staticmethod
    def get_revenue_summary(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> RevenueSummary:
        """Get revenue summary"""
        query = db.query(Orders).filter(
            Orders.advance_amount_status == PaymentStatus.SUCCESSFUL
        )
        
        if start_date:
            query = query.filter(Orders.created_at >= start_date)
        if end_date:
            query = query.filter(Orders.created_at <= end_date)
        
        orders = query.all()
        
        total_revenue = sum(order.total_amount or 0 for order in orders)
        advance_collected = sum(order.pay_advance_amount for order in orders)
        balance_pending = sum(order.pay_at_car or 0 for order in orders)
        deposits_held = sum(order.deposit_amount or 0 for order in orders if not order.deposit_returned)
        refunds_processed = sum(order.refund_amount or 0 for order in orders if order.refund_status == PaymentStatus.REFUNDED)
        
        return RevenueSummary(
            total_revenue=total_revenue,
            advance_collected=advance_collected,
            balance_pending=balance_pending,
            deposits_held=deposits_held,
            refunds_processed=refunds_processed,
            period_start=start_date,
            period_end=end_date
        )
    
    @staticmethod
    def get_cars_currently_rented(db: Session) -> int:
        """Get count of cars currently rented"""
        now = datetime.now()
        return db.query(func.count(func.distinct(Orders.car_id))).filter(
            and_(
                Orders.order_status == BookingStatus.ONGOING,
                Orders.start_time <= now,
                Orders.end_time >= now
            )
        ).scalar() or 0
    
    @staticmethod
    def get_top_performing_cars(db: Session, limit: int = 5) -> List[CarPerformance]:
        """Get top performing cars by bookings and revenue"""
        # Get car performance metrics
        car_stats = db.query(
            Cars.id,
            Cars.brand,
            Cars.car_model,
            func.count(Orders.id).label('total_bookings'),
            func.sum(Orders.total_amount).label('total_revenue'),
            func.avg(Ratings.rating).label('average_rating')
        ).outerjoin(
            Orders, Orders.car_id == Cars.id
        ).outerjoin(
            Ratings, Ratings.car_id == Cars.id
        ).group_by(
            Cars.id, Cars.brand, Cars.car_model
        ).order_by(
            func.count(Orders.id).desc(),
            func.sum(Orders.total_amount).desc()
        ).limit(limit).all()
        
        results = []
        for stat in car_stats:
            car_name = f"{stat.brand} {stat.car_model}"
            results.append(CarPerformance(
                car_id=stat.id,
                car_name=car_name,
                total_bookings=stat.total_bookings or 0,
                total_revenue=float(stat.total_revenue or 0),
                average_rating=float(stat.average_rating) if stat.average_rating else None
            ))
        
        return results
    
    @staticmethod
    def get_least_performing_cars(db: Session, limit: int = 5) -> List[CarPerformance]:
        """Get least performing cars"""
        car_stats = db.query(
            Cars.id,
            Cars.brand,
            Cars.car_model,
            func.count(Orders.id).label('total_bookings'),
            func.sum(Orders.total_amount).label('total_revenue'),
            func.avg(Ratings.rating).label('average_rating')
        ).outerjoin(
            Orders, Orders.car_id == Cars.id
        ).outerjoin(
            Ratings, Ratings.car_id == Cars.id
        ).group_by(
            Cars.id, Cars.brand, Cars.car_model
        ).order_by(
            func.count(Orders.id).asc(),
            func.sum(Orders.total_amount).asc()
        ).limit(limit).all()
        
        results = []
        for stat in car_stats:
            car_name = f"{stat.brand} {stat.car_model}"
            results.append(CarPerformance(
                car_id=stat.id,
                car_name=car_name,
                total_bookings=stat.total_bookings or 0,
                total_revenue=float(stat.total_revenue or 0),
                average_rating=float(stat.average_rating) if stat.average_rating else None
            ))
        
        return results
    
    @staticmethod
    def get_user_growth(db: Session, days: int = 30) -> Dict[str, int]:
        """Get user growth metrics"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Group by day
        daily_counts = db.query(
            func.date(UserProfile.created_at).label('date'),
            func.count(UserProfile.id).label('count')
        ).filter(
            UserProfile.created_at >= start_date
        ).group_by(
            func.date(UserProfile.created_at)
        ).all()
        
        growth = {}
        for daily in daily_counts:
            date_str = daily.date.strftime('%Y-%m-%d') if hasattr(daily.date, 'strftime') else str(daily.date)
            growth[date_str] = daily.count
        
        return growth
    
    @staticmethod
    def get_category_performance(db: Session) -> Dict[str, Dict]:
        """Get performance by car category"""
        category_stats = db.query(
            Cars.car_type,
            func.count(Orders.id).label('bookings'),
            func.sum(Orders.total_amount).label('revenue'),
            func.avg(Ratings.rating).label('avg_rating')
        ).outerjoin(
            Orders, Orders.car_id == Cars.id
        ).outerjoin(
            Ratings, Ratings.car_id == Cars.id
        ).group_by(
            Cars.car_type
        ).all()
        
        performance = {}
        for stat in category_stats:
            performance[stat.car_type.value] = {
                'bookings': stat.bookings or 0,
                'revenue': float(stat.revenue or 0),
                'average_rating': float(stat.avg_rating) if stat.avg_rating else None
            }
        
        return performance
    
    @staticmethod
    def get_booking_timeseries(db: Session, days: int = 30) -> Dict[str, int]:
        """Get booking counts over time"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Group by day
        daily_counts = db.query(
            func.date(Orders.created_at).label('date'),
            func.count(Orders.id).label('count')
        ).filter(
            Orders.created_at >= start_date
        ).group_by(
            func.date(Orders.created_at)
        ).all()
        
        timeseries = {}
        for daily in daily_counts:
            date_str = daily.date.strftime('%Y-%m-%d') if hasattr(daily.date, 'strftime') else str(daily.date)
            timeseries[date_str] = daily.count
        
        return timeseries
    
    @staticmethod
    def get_revenue_timeseries(db: Session, days: int = 30) -> Dict[str, float]:
        """Get revenue over time"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Group by day
        daily_revenue = db.query(
            func.date(Orders.created_at).label('date'),
            func.sum(Orders.total_amount).label('revenue')
        ).filter(
            and_(
                Orders.created_at >= start_date,
                Orders.advance_amount_status == PaymentStatus.SUCCESSFUL
            )
        ).group_by(
            func.date(Orders.created_at)
        ).all()
        
        timeseries = {}
        for daily in daily_revenue:
            date_str = daily.date.strftime('%Y-%m-%d') if hasattr(daily.date, 'strftime') else str(daily.date)
            timeseries[date_str] = float(daily.revenue or 0)
        
        return timeseries
    
    @staticmethod
    def get_dashboard_stats(db: Session, days: int = 30) -> DashboardStats:
        """Get complete dashboard statistics"""
        booking_summary = AnalyticsService.get_booking_summary(db)
        revenue_summary = AnalyticsService.get_revenue_summary(db)
        cars_rented = AnalyticsService.get_cars_currently_rented(db)
        top_cars = AnalyticsService.get_top_performing_cars(db, limit=5)
        least_cars = AnalyticsService.get_least_performing_cars(db, limit=5)
        user_growth = AnalyticsService.get_user_growth(db, days=days)
        category_performance = AnalyticsService.get_category_performance(db)
        booking_timeseries = AnalyticsService.get_booking_timeseries(db, days=days)
        revenue_timeseries = AnalyticsService.get_revenue_timeseries(db, days=days)
        
        return DashboardStats(
            bookings_summary=booking_summary,
            revenue_summary=revenue_summary,
            cars_currently_rented=cars_rented,
            top_performing_cars=top_cars,
            least_performing_cars=least_cars,
            user_growth=user_growth,
            category_performance=category_performance,
            booking_timeseries=booking_timeseries,
            revenue_timeseries=revenue_timeseries
        )


# Global instance
analytics_service = AnalyticsService()

