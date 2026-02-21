from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import math
from app.db.session import get_db
from app.db.models import Cars, Orders, BookingStatus, PaymentStatus, UserProfile
from app.schemas.booking import MobileBookingRequest, MobileBookingResponse, MobileMyBookingsResponse
from app.routes.mobile import get_current_user

router = APIRouter()

@router.post("/", response_model=MobileBookingResponse)
async def create_mobile_booking(
    booking_in: MobileBookingRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new car booking for mobile.
    Validates availability and calculates total price based on days.
    Returns JSON booking confirmation.
    """
    # 1. Car must exist
    car = db.query(Cars).filter(Cars.id == booking_in.car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    # 2. start_datetime must be before end_datetime
    if booking_in.start_datetime >= booking_in.end_datetime:
        raise HTTPException(status_code=400, detail="Start time must be before end time")

    # 3. Booking duration must be positive
    duration = booking_in.end_datetime - booking_in.start_datetime
    if duration.total_seconds() <= 0:
        raise HTTPException(status_code=400, detail="Booking duration must be positive")

    # 4. Check for overlapping bookings
    overlap = db.query(Orders).filter(
        and_(
            Orders.car_id == booking_in.car_id,
            Orders.order_status.in_([
                BookingStatus.PENDING,
                BookingStatus.APPROVED,
                BookingStatus.BOOKED,
                BookingStatus.ONGOING
            ]),
            Orders.start_time < booking_in.end_datetime,
            Orders.end_time > booking_in.start_datetime
        )
    ).first()

    if overlap:
        raise HTTPException(status_code=400, detail="Car already booked for selected dates")

    # 5. Calculate price
    # Determine price_per_day
    price_per_day = float(car.base_price)
    if car.prices and isinstance(car.prices, dict) and 'daily' in car.prices:
        try:
            price_per_day = float(car.prices['daily'])
        except (ValueError, TypeError):
            pass
            
    # Calculate days (round up to nearest day)
    days = math.ceil(duration.total_seconds() / (24 * 3600))
    if days <= 0:
        days = 1
        
    total_price = price_per_day * days

    # 6. Create booking record
    new_booking = Orders(
        user_id=current_user.id,
        car_id=car.id,
        start_time=booking_in.start_datetime,
        end_time=booking_in.end_datetime,
        total_amount=total_price,
        pay_advance_amount=total_price,
        advance_amount_status=PaymentStatus.INITIATED,
        order_status=BookingStatus.PENDING,
        home_delivery=False
    )
    
    try:
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        
        return {
            "booking_id": new_booking.id,
            "car_id": new_booking.car_id,
            "total_price": float(new_booking.total_amount),
            "status": "PENDING",
            "start_datetime": new_booking.start_time,
            "end_datetime": new_booking.end_time
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/my", response_model=MobileMyBookingsResponse)
async def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Fetch logged-in user's bookings for mobile.
    Ordered by start_datetime DESC.
    """
    bookings = db.query(Orders).filter(
        Orders.user_id == current_user.id
    ).order_by(Orders.start_time.desc()).all()
    
    result = []
    for b in bookings:
        result.append({
            "booking_id": b.id,
            "car_id": b.car_id,
            "car_brand": b.car.brand if b.car else "Unknown",
            "car_model": b.car.car_model if b.car else "Unknown",
            "start_datetime": b.start_time,
            "end_datetime": b.end_time,
            "total_price": float(b.total_amount) if b.total_amount else 0.0,
            "status": b.order_status.value if hasattr(b.order_status, 'value') else str(b.order_status)
        })
        
    return {
        "total": len(result),
        "bookings": result
    }

@router.post("/{booking_id}/cancel")
async def cancel_mobile_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Cancel an existing booking for mobile.
    Validates ownership, status, and time constraints.
    Returns JSON confirmation.
    """
    # 1. Booking must exist
    booking = db.query(Orders).filter(Orders.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # 2. Booking must belong to current_user
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")

    # 3. Check current status
    if booking.order_status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Booking is already cancelled")
    
    # Check if status is cancellable (interpreting 'CONFIRMED' as BOOKED or APPROVED)
    if booking.order_status not in [BookingStatus.BOOKED, BookingStatus.APPROVED, BookingStatus.PENDING]:
        raise HTTPException(status_code=400, detail=f"Booking in status {booking.order_status} cannot be cancelled")

    # 4. Business rule: Cannot cancel if start_datetime is in the past
    if booking.start_time < datetime.now():
        raise HTTPException(status_code=400, detail="Cannot cancel a booking that has already started or passed")

    # 5. Update status
    try:
        booking.order_status = BookingStatus.CANCELLED
        booking.cancelled_by = current_user.id
        booking.cancelled_at = datetime.now()
        
        db.commit()
        db.refresh(booking)
        
        return {
            "message": "Booking cancelled successfully",
            "booking_id": booking.id,
            "status": "CANCELLED"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
