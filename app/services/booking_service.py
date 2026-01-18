"""
Booking management service
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.db.models import Orders, Cars, UserProfile, BookingStatus, PaymentStatus
from app.db.models import PaymentLog
from app.schemas.booking import BookingUpdate, BookingCancel
from app.core.logging_config import logger
from app.utils.price_utils import calculate_price


class BookingService:
    """Service for booking management operations"""
    
    @staticmethod
    def get_bookings(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[BookingStatus] = None,
        user_id: Optional[int] = None,
        car_id: Optional[int] = None
    ) -> List[Orders]:
        """Get list of bookings with filters"""
        query = db.query(Orders)
        
        if status:
            query = query.filter(Orders.order_status == status)
        
        if user_id:
            query = query.filter(Orders.user_id == user_id)
        
        if car_id:
            query = query.filter(Orders.car_id == car_id)
        
        return query.order_by(Orders.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_booking(db: Session, booking_id: int) -> Optional[Orders]:
        """Get booking by ID"""
        return db.query(Orders).filter(Orders.id == booking_id).first()
    
    @staticmethod
    def update_booking(
        db: Session,
        booking_id: int,
        booking_data: BookingUpdate,
        updated_by: int
    ) -> Optional[Orders]:
        """Update booking"""
        try:
            booking = db.query(Orders).filter(Orders.id == booking_id).first()
            if not booking:
                return None
            
            update_data = booking_data.dict(exclude_unset=True)
            
            # If updating status to ONGOING, set actual_start_time
            if booking_data.order_status == BookingStatus.ONGOING and not booking.actual_start_time:
                update_data['actual_start_time'] = datetime.now()
            
            # If updating status to COMPLETED, set actual_end_time and calculate charges
            if booking_data.order_status == BookingStatus.COMPLETED:
                if not booking.actual_end_time:
                    update_data['actual_end_time'] = datetime.now()
                
                # Calculate late return charges if applicable
                if booking.actual_end_time and booking.end_time:
                    if booking.actual_end_time > booking.end_time:
                        hours_late = (booking.actual_end_time - booking.end_time).total_seconds() / 3600
                        # Calculate extra hours charge (assuming hourly rate from car prices)
                        if booking.car.prices and booking.car.prices.get('hourly'):
                            hourly_rate = booking.car.prices['hourly']
                            extra_hours_charge = hours_late * hourly_rate
                            update_data['extra_hours_charge'] = extra_hours_charge
            
            for key, value in update_data.items():
                setattr(booking, key, value)
            
            db.commit()
            db.refresh(booking)
            
            logger.info(f"Booking updated: {booking_id}")
            return booking
            
        except Exception as e:
            logger.error(f"Error updating booking: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def cancel_booking(
        db: Session,
        booking_id: int,
        cancel_data: BookingCancel,
        cancelled_by: int
    ) -> Optional[Orders]:
        """Cancel a booking with refund logic"""
        try:
            booking = db.query(Orders).filter(Orders.id == booking_id).first()
            if not booking:
                return None
            
            # Update booking status
            booking.order_status = BookingStatus.CANCELLED
            booking.cancellation_reason = cancel_data.cancellation_reason
            booking.cancelled_by = cancelled_by
            booking.cancelled_at = datetime.now()
            
            # Calculate refund if applicable
            if booking.advance_amount_status == PaymentStatus.SUCCESSFUL:
                # Refund policy: full refund if cancelled 24+ hours before start
                hours_before_start = (booking.start_time - datetime.now()).total_seconds() / 3600
                
                if hours_before_start >= 24:
                    refund_amount = booking.pay_advance_amount
                elif hours_before_start >= 12:
                    refund_amount = booking.pay_advance_amount * 0.5  # 50% refund
                else:
                    refund_amount = 0  # No refund if less than 12 hours
                
                booking.refund_amount = refund_amount
                booking.refund_status = PaymentStatus.REFUND_INITIATED
                
                # Create payment log for refund
                payment_log = PaymentLog(
                    order_id=booking.id,
                    user_id=booking.user_id,
                    amount=refund_amount,
                    payment_type="REFUND",
                    payment_status=PaymentStatus.REFUND_INITIATED,
                    payment_gateway="CCAVENUE"
                )
                db.add(payment_log)
            
            db.commit()
            db.refresh(booking)
            
            logger.info(f"Booking cancelled: {booking_id}, Refund: {booking.refund_amount}")
            return booking
            
        except Exception as e:
            logger.error(f"Error cancelling booking: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def get_upcoming_bookings(db: Session, days: int = 7) -> List[Orders]:
        """Get upcoming bookings in next N days"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        
        return db.query(Orders).filter(
            and_(
                Orders.order_status.in_([BookingStatus.PENDING, BookingStatus.APPROVED, BookingStatus.BOOKED]),
                Orders.start_time >= start_date,
                Orders.start_time <= end_date
            )
        ).order_by(Orders.start_time.asc()).all()
    
    @staticmethod
    def get_ongoing_bookings(db: Session) -> List[Orders]:
        """Get currently ongoing bookings"""
        now = datetime.now()
        
        return db.query(Orders).filter(
            and_(
                Orders.order_status == BookingStatus.ONGOING,
                Orders.start_time <= now,
                Orders.end_time >= now
            )
        ).all()
    
    @staticmethod
    def get_completed_bookings(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Orders]:
        """Get completed bookings"""
        return db.query(Orders).filter(
            Orders.order_status == BookingStatus.COMPLETED
        ).order_by(Orders.updated_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def assign_car(
        db: Session,
        booking_id: int,
        car_id: int,
        assigned_by: int
    ) -> Optional[Orders]:
        """Assign/reassign car to booking"""
        booking = db.query(Orders).filter(Orders.id == booking_id).first()
        if not booking:
            return None
        
        booking.car_id = car_id
        booking.assigned_by = assigned_by
        db.commit()
        db.refresh(booking)
        
        return booking


# Global instance
booking_service = BookingService()

