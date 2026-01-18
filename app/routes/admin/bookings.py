"""
Admin routes for booking management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.booking import BookingResponse, BookingUpdate, BookingCancel
from app.services.booking_service import booking_service
from app.routes.admin.dependencies import require_admin
from app.utils.pagination import paginate_query, PaginatedResponse
from app.db.models import BookingStatus

router = APIRouter(
    prefix="/admin/api/bookings",  # Changed to /admin/api/bookings to avoid conflict with page routes
    tags=["admin-bookings"]
)


@router.get("", response_model=PaginatedResponse[BookingResponse])
async def list_bookings(
    page: int = 1,
    page_size: int = 20,
    status: Optional[BookingStatus] = None,
    user_id: Optional[int] = None,
    car_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all bookings with pagination"""
    skip = (page - 1) * page_size
    
    bookings = booking_service.get_bookings(
        db=db,
        skip=skip,
        limit=page_size,
        status=status,
        user_id=user_id,
        car_id=car_id
    )
    
    from app.db.models import Orders, UserProfile, Cars
    total_query = db.query(Orders)
    if status:
        total_query = total_query.filter(Orders.order_status == status)
    if user_id:
        total_query = total_query.filter(Orders.user_id == user_id)
    if car_id:
        total_query = total_query.filter(Orders.car_id == car_id)
    
    total = total_query.count()
    
    # Get all unique user IDs and car IDs from bookings
    user_ids = list(set([b.user_id for b in bookings if b.user_id]))
    car_ids = list(set([b.car_id for b in bookings if b.car_id]))
    
    # Bulk fetch users and cars
    users_dict = {}
    if user_ids:
        users = db.query(UserProfile).filter(UserProfile.id.in_(user_ids)).all()
        users_dict = {user.id: user for user in users}
    
    cars_dict = {}
    if car_ids:
        cars = db.query(Cars).filter(Cars.id.in_(car_ids)).all()
        cars_dict = {car.id: car for car in cars}
    
    # Enrich bookings with user and car details
    enriched_bookings = []
    for booking in bookings:
        # Convert booking to dict
        booking_dict = {
            "id": booking.id,
            "user_id": booking.user_id,
            "car_id": booking.car_id,
            "coupon_id": booking.coupon_id,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "actual_start_time": booking.actual_start_time,
            "actual_end_time": booking.actual_end_time,
            "order_status": booking.order_status,
            "pay_advance_amount": booking.pay_advance_amount,
            "advance_amount_status": booking.advance_amount_status,
            "total_amount": booking.total_amount,
            "extra_hours_charge": booking.extra_hours_charge,
            "extra_km_charge": booking.extra_km_charge,
            "deposit_amount": booking.deposit_amount,
            "no_of_km_travelled": booking.no_of_km_travelled,
            "pickup_location": booking.pickup_location,
            "drop_location": booking.drop_location,
            "home_delivery": booking.home_delivery,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at,
            "user_firstname": None,
            "user_lastname": None,
            "car_brand": None,
            "car_model": None
        }
        
        # Get user details from pre-fetched dict
        if booking.user_id and booking.user_id in users_dict:
            user = users_dict[booking.user_id]
            booking_dict["user_firstname"] = user.firstname
            booking_dict["user_lastname"] = user.lastname
        
        # Get car details from pre-fetched dict
        if booking.car_id and booking.car_id in cars_dict:
            car = cars_dict[booking.car_id]
            booking_dict["car_brand"] = car.brand
            booking_dict["car_model"] = car.car_model
        
        enriched_bookings.append(BookingResponse(**booking_dict))
    
    return PaginatedResponse(
        items=enriched_bookings,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=page * page_size < total,
        has_prev=page > 1
    )


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get booking by ID"""
    booking = booking_service.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    from app.db.models import UserProfile, Cars
    
    # Enrich booking with user and car details
    booking_dict = {
        **booking.__dict__,
        "user_firstname": None,
        "user_lastname": None,
        "car_brand": None,
        "car_model": None
    }
    
    # Get user details
    if booking.user_id:
        user = db.query(UserProfile).filter(UserProfile.id == booking.user_id).first()
        if user:
            booking_dict["user_firstname"] = user.firstname
            booking_dict["user_lastname"] = user.lastname
    
    # Get car details
    if booking.car_id:
        car = db.query(Cars).filter(Cars.id == booking.car_id).first()
        if car:
            booking_dict["car_brand"] = car.brand
            booking_dict["car_model"] = car.car_model
    
    return BookingResponse(**booking_dict)


@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: int,
    booking_data: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update booking"""
    booking = booking_service.update_booking(
        db, booking_id, booking_data, current_user["user_id"]
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: int,
    cancel_data: BookingCancel,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Cancel a booking with refund"""
    booking = booking_service.cancel_booking(
        db, booking_id, cancel_data, current_user["user_id"]
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("/upcoming/list", response_model=List[BookingResponse])
async def get_upcoming_bookings(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get upcoming bookings"""
    return booking_service.get_upcoming_bookings(db, days)


@router.get("/ongoing/list", response_model=List[BookingResponse])
async def get_ongoing_bookings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get currently ongoing bookings"""
    return booking_service.get_ongoing_bookings(db)


@router.post("/{booking_id}/assign-car", response_model=BookingResponse)
async def assign_car(
    booking_id: int,
    car_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Assign/reassign car to booking"""
    booking = booking_service.assign_car(
        db, booking_id, car_id, current_user["user_id"]
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

