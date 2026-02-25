"""
Admin routes for car management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.schemas.car import CarCreate, CarUpdate, CarResponse, CarAvailabilityCreate, CarAvailabilityResponse
from app.services.car_service import car_service
from app.routes.admin.dependencies import require_admin
from app.utils.pagination import paginate_query, PaginatedResponse
from app.core.logging_config import logger

router = APIRouter(
    prefix="/admin/api/cars",  # Changed to /admin/api/cars to avoid conflict with page routes
    tags=["admin-cars"]
)


@router.get("", response_model=PaginatedResponse[CarResponse])
async def list_cars(
    page: int = 1,
    page_size: int = 20,
    active_only: bool = False,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all cars with pagination"""
    skip = (page - 1) * page_size
    
    cars = car_service.get_cars(
        db=db,
        skip=skip,
        limit=page_size,
        active_only=active_only,
        search=search
    )
    
    # Get total count for pagination
    from app.db.models import Cars
    total_query = db.query(Cars)
    if active_only:
        total_query = total_query.filter(Cars.active == True)
    if search:
        like_pattern = f"%{search}%"
        total_query = total_query.filter(
            or_(
                Cars.registration_number.ilike(like_pattern),
                Cars.brand.ilike(like_pattern),
                Cars.car_model.ilike(like_pattern)
            )
        )
    
    total = total_query.count()
    
    return PaginatedResponse(
        items=cars,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=page * page_size < total,
        has_prev=page > 1
    )


@router.get("/{car_id}", response_model=CarResponse)
async def get_car(
    car_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get car by ID"""
    car = car_service.get_car(db, car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return car


@router.post("", response_model=CarResponse, status_code=status.HTTP_201_CREATED)
async def create_car(
    brand: str = Form(...),
    car_model: str = Form(...),
    description: str = Form(None),
    base_price: float = Form(...),
    damage_price: float = Form(...),
    protection_price: float = Form(...),
    no_of_km: int = Form(...),
    fuel_type: str = Form(...),
    transmission_type: str = Form(...),
    no_of_seats: str = Form(...),
    car_type: str = Form(...),
    location_id: int = Form(None),
    maps_link: str = Form(None),
    registration_number: str = Form(None),
    year: int = Form(None),
    color: str = Form(None),
    is_top_selling: bool = Form(False),
    is_premium: bool = Form(False),
    active: bool = Form(True),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create a new car"""
    from app.db.models import FuelType, TransmissionType, NoOfSeats, CarType
    
    try:
        car_data = CarCreate(
            brand=brand,
            car_model=car_model,
            description=description,
            base_price=base_price,
            damage_price=damage_price,
            protection_price=protection_price,
            no_of_km=no_of_km,
            fuel_type=FuelType(fuel_type),
            transmission_type=TransmissionType(transmission_type),
            no_of_seats=NoOfSeats(no_of_seats),
            car_type=CarType(car_type),
            location_id=location_id,
            maps_link=maps_link,
            registration_number=registration_number,
            year=year,
            color=color,
            is_top_selling=is_top_selling,
            is_premium=is_premium,
            active=active
        )
        
        car = await car_service.create_car(db, car_data, images)
        return car
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating car: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating car")


@router.put("/{car_id}", response_model=CarResponse)
async def update_car(
    car_id: int,
    brand: str = Form(None),
    car_model: str = Form(None),
    description: str = Form(None),
    base_price: float = Form(None),
    damage_price: float = Form(None),
    protection_price: float = Form(None),
    no_of_km: int = Form(None),
    fuel_type: str = Form(None),
    transmission_type: str = Form(None),
    no_of_seats: str = Form(None),
    car_type: str = Form(None),
    location_id: int = Form(None),
    maps_link: str = Form(None),
    registration_number: str = Form(None),
    year: int = Form(None),
    color: str = Form(None),
    is_top_selling: bool = Form(None),
    is_premium: bool = Form(None),
    active: bool = Form(None),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update a car"""
    from app.db.models import FuelType, TransmissionType, NoOfSeats, CarType
    
    try:
        # Build update data dict with only provided fields
        update_data = {}
        if brand is not None:
            update_data['brand'] = brand
        if car_model is not None:
            update_data['car_model'] = car_model
        if description is not None:
            update_data['description'] = description
        if base_price is not None:
            update_data['base_price'] = base_price
        if damage_price is not None:
            update_data['damage_price'] = damage_price
        if protection_price is not None:
            update_data['protection_price'] = protection_price
        if no_of_km is not None:
            update_data['no_of_km'] = no_of_km
        if fuel_type is not None:
            update_data['fuel_type'] = FuelType(fuel_type)
        if transmission_type is not None:
            update_data['transmission_type'] = TransmissionType(transmission_type)
        if no_of_seats is not None:
            update_data['no_of_seats'] = NoOfSeats(no_of_seats)
        if car_type is not None:
            update_data['car_type'] = CarType(car_type)
        if location_id is not None:
            update_data['location_id'] = location_id
        if maps_link is not None:
            update_data['maps_link'] = maps_link
        if registration_number is not None:
            update_data['registration_number'] = registration_number
        if year is not None:
            update_data['year'] = year
        if color is not None:
            update_data['color'] = color
        if is_top_selling is not None:
            update_data['is_top_selling'] = is_top_selling
        if is_premium is not None:
            update_data['is_premium'] = is_premium
        if active is not None:
            update_data['active'] = active
        
        car_data = CarUpdate(**update_data)
        car = await car_service.update_car(db, car_id, car_data, images)
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        return car
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating car: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating car")


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(
    car_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Delete a car"""
    success = car_service.delete_car(db, car_id)
    if not success:
        raise HTTPException(status_code=404, detail="Car not found")


@router.post("/{car_id}/toggle-active", response_model=CarResponse)
async def toggle_car_active(
    car_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Toggle car active status"""
    car = car_service.toggle_car_active(db, car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return car


@router.post("/{car_id}/availability", response_model=CarAvailabilityResponse)
async def block_availability(
    car_id: int,
    availability_data: CarAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Block car availability for a period"""
    availability = car_service.block_car_availability(
        db, car_id, availability_data, current_user["user_id"]
    )
    return availability


@router.get("/{car_id}/availability", response_model=List[CarAvailabilityResponse])
async def get_availability(
    car_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get availability blocks for a car"""
    return car_service.get_car_availability(db, car_id)

