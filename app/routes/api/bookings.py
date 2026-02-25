"""
Mobile booking endpoints
  POST /api/bookings/calculate        – price estimation (no booking created)
  POST /api/bookings/                 – create a booking (status=PENDING)
  GET  /api/bookings/my               – list logged-in user's bookings
  GET  /api/bookings/{booking_id}     – single booking detail
  POST /api/bookings/{booking_id}/cancel – cancel booking
"""
import math
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import get_db
from app.db.models import Cars, Orders, CarAvailability, BookingStatus, PaymentStatus, UserProfile
from app.routes.mobile import get_current_user
from app.schemas.booking import (
    MobileBookingRequest,
    MobileBookingResponse,
    MobileMyBookingsResponse,
)
from app.schemas.mobile import (
    MobileBookingCalculateRequest,
    MobileBookingCalculateResponse,
    MobileBookingDetailResponse,
    MobileBookingCancelResponse,
)

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_price_per_day(car: Cars) -> float:
    """Return the daily price for a car (prices.daily or base_price fallback)."""
    if car.prices and isinstance(car.prices, dict) and "daily" in car.prices:
        try:
            return float(car.prices["daily"])
        except (ValueError, TypeError):
            pass
    return float(car.base_price)


def _get_deposit(car: Cars) -> float:
    """Return the security deposit for a car (prices.deposit or 0)."""
    if car.prices and isinstance(car.prices, dict) and "deposit" in car.prices:
        try:
            return float(car.prices["deposit"])
        except (ValueError, TypeError):
            pass
    return 0.0


def _check_car_overlap(db: Session, car_id: int, pickup: datetime, ret: datetime, exclude_booking_id: int = None):
    """
    Returns True if the car is unavailable for [pickup, ret) due to:
      - An active booking (PENDING / APPROVED / BOOKED / ONGOING)
      - A CarAvailability block
    """
    booking_q = db.query(Orders).filter(
        Orders.car_id == car_id,
        Orders.order_status.in_([
            BookingStatus.PENDING,
            BookingStatus.APPROVED,
            BookingStatus.BOOKED,
            BookingStatus.ONGOING,
        ]),
        Orders.end_time > pickup,
        Orders.start_time < ret,
    )
    if exclude_booking_id:
        booking_q = booking_q.filter(Orders.id != exclude_booking_id)

    if booking_q.first():
        return True

    block = db.query(CarAvailability).filter(
        CarAvailability.car_id == car_id,
        CarAvailability.end_date > pickup,
        CarAvailability.start_date < ret,
    ).first()
    return block is not None


def _booking_to_detail(b: Orders) -> dict:
    return {
        "booking_id": b.id,
        "car_id": b.car_id,
        "car_brand": b.car.brand if b.car else "Unknown",
        "car_model": b.car.car_model if b.car else "Unknown",
        "start_datetime": b.start_time,
        "end_datetime": b.end_time,
        "status": b.order_status.value if hasattr(b.order_status, "value") else str(b.order_status),
        "total_price": float(b.total_amount) if b.total_amount else 0.0,
        "cancellation_reason": b.cancellation_reason,
        "created_at": b.created_at,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/calculate", response_model=MobileBookingCalculateResponse)
async def calculate_booking_price(
    req: MobileBookingCalculateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Estimate the cost of a booking without creating one.
    Returns days, base_price, damage_protection, security_deposit, and total.
    """
    car = db.query(Cars).filter(Cars.id == req.car_id, Cars.active == True).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found or inactive")

    if req.pickup_datetime >= req.return_datetime:
        raise HTTPException(status_code=400, detail="pickup_datetime must be before return_datetime")

    duration = req.return_datetime - req.pickup_datetime
    days = math.ceil(duration.total_seconds() / (24 * 3600))
    if days <= 0:
        days = 1

    price_per_day = _get_price_per_day(car)
    security_deposit = _get_deposit(car)
    damage_protection = float(req.damage_protection or 0)
    base_price = price_per_day * days
    total = base_price + damage_protection + security_deposit

    return {
        "days": days,
        "base_price": round(base_price, 2),
        "damage_protection": round(damage_protection, 2),
        "security_deposit": round(security_deposit, 2),
        "total": round(total, 2),
    }


@router.post("/", response_model=MobileBookingResponse)
async def create_mobile_booking(
    booking_in: MobileBookingRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Create a new car booking using an atomic transaction with row-level locking.
    Prevents race conditions by locking the car record before checking availability.
    """
    try:
        # Start transaction (Explicitly start if needed, but Session handles it)
        # Lock the car row to prevent simultaneous checks for the same car
        car = (
            db.query(Cars)
            .filter(Cars.id == booking_in.car_id, Cars.active == True)
            .with_for_update()
            .first()
        )

        if not car:
            raise HTTPException(status_code=404, detail="Car not found or inactive")

        # Basic validation
        if booking_in.start_datetime >= booking_in.end_datetime:
            raise HTTPException(status_code=400, detail="Start time must be before end time")

        duration = booking_in.end_datetime - booking_in.start_datetime
        if duration.total_seconds() <= 0:
            raise HTTPException(status_code=400, detail="Booking duration must be positive")

        # ── OVERLAP CHECK: Bookings ──
        # Logic: NOT (existing.end_datetime <= new.start_datetime OR existing.start_datetime >= new.end_datetime)
        # Which simplifies to: existing.end_datetime > new.start_datetime AND existing.start_datetime < new.end_datetime
        overlap_booking = db.query(Orders).filter(
            Orders.car_id == car.id,
            Orders.order_status.in_([
                BookingStatus.PENDING,
                BookingStatus.APPROVED,
                BookingStatus.BOOKED,
                BookingStatus.ONGOING,
            ]),
            Orders.end_time > booking_in.start_datetime,
            Orders.start_time < booking_in.end_datetime,
        ).first()

        if overlap_booking:
            raise HTTPException(status_code=400, detail="Car not available (overlapping booking exists)")

        # ── OVERLAP CHECK: CarAvailability blocks ──
        overlap_block = db.query(CarAvailability).filter(
            CarAvailability.car_id == car.id,
            CarAvailability.end_date > booking_in.start_datetime,
            CarAvailability.start_date < booking_in.end_datetime,
        ).first()

        if overlap_block:
            raise HTTPException(status_code=400, detail="Car not available (maintenance or block exist)")

        # ── CALCULATION ──
        days = math.ceil(duration.total_seconds() / (24 * 3600))
        if days <= 0:
            days = 1

        price_per_day = _get_price_per_day(car)
        total_price = price_per_day * days

        # ── CREATE BOOKING ──
        new_booking = Orders(
            user_id=current_user.id,
            car_id=car.id,
            start_time=booking_in.start_datetime,
            end_time=booking_in.end_datetime,
            total_amount=total_price,
            pay_advance_amount=total_price,
            advance_amount_status=PaymentStatus.INITIATED,
            order_status=BookingStatus.PENDING,
            home_delivery=False,
        )

        db.add(new_booking)
        db.commit()  # Committing releases the car row lock
        db.refresh(new_booking)

        return {
            "booking_id": new_booking.id,
            "car_id": new_booking.car_id,
            "total_price": float(new_booking.total_amount),
            "status": "PENDING",
            "start_datetime": new_booking.start_time,
            "end_datetime": new_booking.end_time,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during booking: {str(e)}"
        )


@router.get("/my", response_model=MobileMyBookingsResponse)
async def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """List all bookings for the logged-in user, newest first."""
    bookings = (
        db.query(Orders)
        .filter(Orders.user_id == current_user.id)
        .order_by(Orders.start_time.desc())
        .all()
    )

    result = [
        {
            "booking_id": b.id,
            "car_id": b.car_id,
            "car_brand": b.car.brand if b.car else "Unknown",
            "car_model": b.car.car_model if b.car else "Unknown",
            "start_datetime": b.start_time,
            "end_datetime": b.end_time,
            "total_price": float(b.total_amount) if b.total_amount else 0.0,
            "status": b.order_status.value if hasattr(b.order_status, "value") else str(b.order_status),
        }
        for b in bookings
    ]
    return {"total": len(result), "bookings": result}


@router.get("/{booking_id}", response_model=MobileBookingDetailResponse)
async def get_booking_detail(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Return full detail for a single booking. Must belong to the current user."""
    booking = db.query(Orders).filter(Orders.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this booking")

    return _booking_to_detail(booking)


@router.post("/{booking_id}/cancel", response_model=MobileBookingCancelResponse)
async def cancel_mobile_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Cancel a booking. Allowed statuses: PENDING, BOOKED (APPROVED also accepted).
    Returns the updated booking JSON.
    """
    booking = db.query(Orders).filter(Orders.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")

    if booking.order_status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Booking is already cancelled")

    if booking.order_status not in [
        BookingStatus.PENDING,
        BookingStatus.APPROVED,
        BookingStatus.BOOKED,
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Booking in status '{booking.order_status.value}' cannot be cancelled",
        )

    if booking.start_time < datetime.now():
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel a booking that has already started or passed",
        )

    try:
        booking.order_status = BookingStatus.CANCELLED
        booking.cancelled_by = current_user.id
        booking.cancelled_at = datetime.now()
        db.commit()
        db.refresh(booking)
        return {
            "booking_id": booking.id,
            "status": "CANCELLED",
            "message": "Booking cancelled successfully",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
