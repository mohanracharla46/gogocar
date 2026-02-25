from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import (
    BookingStatus,
    CarAvailability,
    Cars,
    CarType,
    FuelType,
    Location,
    NoOfSeats,
    Orders,
    TransmissionType,
    UserProfile,
)
from app.db.session import get_db
from app.routes.mobile import get_current_user
from app.schemas.car import CarDetailResponse, MobileCarListing

router = APIRouter()


@router.get("/", response_model=List[MobileCarListing])
async def get_mobile_cars(
    location_id: Optional[int] = Query(None),
    pickup_date: Optional[datetime] = Query(None),
    return_date: Optional[datetime] = Query(None),
    seats: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    # current_user: UserProfile = Depends(get_current_user),
):
    """
    Fetch cars for mobile listing with production-ready filtering.
    Requires JWT Bearer token.
    """
    # 1. Base query: Active cars only
    query = db.query(Cars).filter(Cars.active == True)

    # 2. Location filter (using location_id)
    if location_id:
        query = query.filter(Cars.location_id == location_id)

    # 3. Seats filter
    if seats:
        valid_seats = []
        if seats <= 5:
            valid_seats.extend([NoOfSeats.FIVE, NoOfSeats.SEVEN])
        elif seats <= 7:
            valid_seats.append(NoOfSeats.SEVEN)

        if valid_seats:
            query = query.filter(Cars.no_of_seats.in_(valid_seats))
        else:
            return []

    # 4. Availability filter (pickup_date and return_date)
    if pickup_date and return_date:
        # Exclude cars that have bookings with overlapping dates
        booked_car_ids = (
            db.query(Orders.car_id)
            .filter(
                Orders.order_status.in_(
                    [
                        BookingStatus.PENDING,
                        BookingStatus.APPROVED,
                        BookingStatus.BOOKED,
                        BookingStatus.ONGOING,
                    ]
                ),
                Orders.end_time > pickup_date,
                Orders.start_time < return_date,
            )
            .distinct()
        )

        # Exclude cars blocked in CarAvailability table
        blocked_car_ids = (
            db.query(CarAvailability.car_id)
            .filter(
                CarAvailability.end_date > pickup_date,
                CarAvailability.start_date < return_date,
            )
            .distinct()
        )

        query = query.filter(~Cars.id.in_(booked_car_ids))
        query = query.filter(~Cars.id.in_(blocked_car_ids))

    cars_query = query.all()

    result = []
    for car in cars_query:
        # seats mapping
        seats_map = {NoOfSeats.FIVE: 5, NoOfSeats.SEVEN: 7}

        # Determine price_per_day
        price_per_day = float(car.base_price)
        if car.prices and isinstance(car.prices, dict) and "daily" in car.prices:
            try:
                price_per_day = float(car.prices["daily"])
            except (ValueError, TypeError):
                pass

        # Price range filter
        if min_price is not None and price_per_day < min_price:
            continue
        if max_price is not None and price_per_day > max_price:
            continue

        # image mapping
        first_image = ""
        if car.images:
            images_list = car.images.split(",")
            if images_list:
                first_image = images_list[0].strip()

        # Construct the response object
        car_data = {
            "id": car.id,
            "brand": car.brand,
            "model": car.car_model,
            "price_per_day": price_per_day,
            "fuel_type": car.fuel_type.value
            if hasattr(car.fuel_type, "value")
            else str(car.fuel_type),
            "transmission": car.transmission_type.value
            if hasattr(car.transmission_type, "value")
            else str(car.transmission_type),
            "seats": seats_map.get(car.no_of_seats, 5),
            "image": first_image,
        }
        result.append(car_data)

    return result


@router.get("/{car_id}", response_model=CarDetailResponse)
async def get_mobile_car_detail(
    car_id: int,
    db: Session = Depends(get_db),
    # current_user: UserProfile = Depends(get_current_user),
):
    """
    Fetch car detail by ID for mobile. Requires JWT Bearer token.
    """
    car = db.query(Cars).filter(Cars.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    # seats mapping
    seats_map = {NoOfSeats.FIVE: 5, NoOfSeats.SEVEN: 7}

    # image mapping: take first image from comma-separated string
    first_image = ""
    if car.images:
        images_list = car.images.split(",")
        if images_list:
            first_image = images_list[0].strip()

    # Determine price_per_day
    price_per_day = float(car.base_price)
    if car.prices and isinstance(car.prices, dict) and "daily" in car.prices:
        try:
            price_per_day = float(car.prices["daily"])
        except (ValueError, TypeError):
            pass

    # Features handling
    features = car.features
    if isinstance(features, str):
        import json

        try:
            features = json.loads(features)
        except:
            features = []
    elif features is None:
        features = []

    return {
        "id": car.id,
        "brand": car.brand,
        "model": car.car_model,
        "price_per_day": price_per_day,
        "fuel_type": car.fuel_type.value
        if hasattr(car.fuel_type, "value")
        else str(car.fuel_type),
        "transmission": car.transmission_type.value
        if hasattr(car.transmission_type, "value")
        else str(car.transmission_type),
        "seats": seats_map.get(car.no_of_seats, 5),
        "image": first_image,
        "description": car.description,
        "features": features,
    }
