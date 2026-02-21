from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.db.models import Cars, NoOfSeats, FuelType, TransmissionType, CarType
from app.schemas.car import MobileCarListing, CarDetailResponse
from app.core.config import settings

router = APIRouter()

@router.get("/", response_model=List[MobileCarListing])
async def get_mobile_cars(db: Session = Depends(get_db)):
    """
    Fetch cars for mobile listing.
    Returns JSON list of cars with specific fields.
    Includes temporary debug logging.
    """
    # Debug logging as requested
    print(f"DEBUG MOBILE API: Database URL: {settings.DATABASE_URL}")
    
    # Fetch all cars (no filters as requested)
    cars_query = db.query(Cars).all()
    print(f"DEBUG MOBILE API: Total number of cars fetched: {len(cars_query)}")
    
    result = []
    for car in cars_query:
        # seats mapping: FIVE -> 5, SEVEN -> 7
        seats_map = {
            NoOfSeats.FIVE: 5,
            NoOfSeats.SEVEN: 7
        }
        
        # image mapping: take first image from comma-separated string
        first_image = ""
        if car.images:
            images_list = car.images.split(',')
            if images_list:
                first_image = images_list[0].strip()

        # Determine price_per_day
        # Default to base_price if daily is not specified in JSON
        price_per_day = float(car.base_price)
        if car.prices and isinstance(car.prices, dict) and 'daily' in car.prices:
            try:
                price_per_day = float(car.prices['daily'])
            except (ValueError, TypeError):
                pass

        # Construct the response object
        car_data = {
            "id": car.id,
            "brand": car.brand,
            "model": car.car_model,
            "price_per_day": price_per_day,
            "fuel_type": car.fuel_type.value if hasattr(car.fuel_type, 'value') else str(car.fuel_type),
            "transmission": car.transmission_type.value if hasattr(car.transmission_type, 'value') else str(car.transmission_type),
            "seats": seats_map.get(car.no_of_seats, 5),
            "image": first_image
        }
        result.append(car_data)
            
    return result

@router.get("/{car_id}", response_model=CarDetailResponse)
async def get_mobile_car_detail(car_id: int, db: Session = Depends(get_db)):
    """
    Fetch car detail by ID for mobile.
    Returns JSON object of car details.
    """
    car = db.query(Cars).filter(Cars.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    # seats mapping: FIVE -> 5, SEVEN -> 7
    seats_map = {
        NoOfSeats.FIVE: 5,
        NoOfSeats.SEVEN: 7
    }
    
    # image mapping: take first image from comma-separated string
    first_image = ""
    if car.images:
        images_list = car.images.split(',')
        if images_list:
            first_image = images_list[0].strip()

    # Determine price_per_day
    price_per_day = float(car.base_price)
    if car.prices and isinstance(car.prices, dict) and 'daily' in car.prices:
        try:
            price_per_day = float(car.prices['daily'])
        except (ValueError, TypeError):
            pass

    # Features handling (stored as JSON in DB, but might be a string in some SQLite setups)
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
        "fuel_type": car.fuel_type.value if hasattr(car.fuel_type, 'value') else str(car.fuel_type),
        "transmission": car.transmission_type.value if hasattr(car.transmission_type, 'value') else str(car.transmission_type),
        "seats": seats_map.get(car.no_of_seats, 5),
        "image": first_image,
        "description": car.description,
        "features": features
    }
