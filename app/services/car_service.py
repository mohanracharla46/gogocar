"""
Car management service
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import Cars, CarAvailability, Location
from app.db.models import FuelType, TransmissionType, NoOfSeats, CarType
from app.schemas.car import CarCreate, CarUpdate, CarAvailabilityCreate
from app.core.logging_config import logger
from app.utils.s3_service import s3_service


class CarService:
    """Service for car management operations"""
    
    @staticmethod
    async def create_car(db: Session, car_data: CarCreate, images: Optional[List] = None) -> Cars:
        """
        Create a new car
        
        Args:
            db: Database session
            car_data: Car creation data
            images: Optional list of image files
            
        Returns:
            Created car object
        """
        try:
            # Create car first (without images)
            car = Cars(
                brand=car_data.brand,
                car_model=car_data.car_model,
                description=car_data.description,
                base_price=car_data.base_price,
                damage_price=car_data.damage_price,
                protection_price=car_data.protection_price,
                no_of_km=car_data.no_of_km,
                fuel_type=car_data.fuel_type,
                transmission_type=car_data.transmission_type,
                no_of_seats=car_data.no_of_seats,
                car_type=car_data.car_type,
                location_id=car_data.location_id,
                maps_link=car_data.maps_link,
                prices=car_data.prices,
                features=car_data.features,
                tags=car_data.tags,
                registration_number=car_data.registration_number,
                year=car_data.year,
                color=car_data.color,
                active=car_data.active,
                is_top_selling=car_data.is_top_selling,
                is_premium=car_data.is_premium,
                images=None  # Will be set after upload
            )
            
            db.add(car)
            db.commit()
            db.refresh(car)
            
            # Upload images after car is created (with correct car_id)
            image_urls = []
            if images:
                for image_file in images:
                    try:
                        # Reset file pointer before reading
                        await image_file.seek(0)
                        url = await s3_service.upload_car_image(image_file, car.id)
                        image_urls.append(url)
                    except Exception as e:
                        logger.error(f"Error uploading image: {str(e)}")
                        # Fail fast if credentials are missing or invalid
                        if "Unable to locate credentials" in str(e) or "InvalidCredentials" in str(e) or "Access Denied" in str(e) or "ClientError" in str(e):
                            raise Exception(f"S3 Upload Failed: {str(e)}")
                
                # Update car with image URLs
                if image_urls:
                    car.images = ",".join(image_urls)
                    db.commit()
                    db.refresh(car)
            
            logger.info(f"Car created: {car.id} - {car.brand} {car.car_model}")
            return car
            
        except Exception as e:
            logger.error(f"Error creating car: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    async def update_car(db: Session, car_id: int, car_data: CarUpdate, images: Optional[List] = None) -> Optional[Cars]:
        """
        Update an existing car
        
        Args:
            db: Database session
            car_id: Car ID
            car_data: Car update data
            images: Optional list of new image files
            
        Returns:
            Updated car object or None
        """
        try:
            car = db.query(Cars).filter(Cars.id == car_id).first()
            if not car:
                return None
            
            # Update fields
            update_data = car_data.dict(exclude_unset=True)
            if images:
                # Upload new images
                new_image_urls = []
                for image_file in images:
                    try:
                        # Reset file pointer before reading
                        await image_file.seek(0)
                        url = await s3_service.upload_car_image(image_file, car_id)
                        new_image_urls.append(url)
                    except Exception as e:
                        logger.error(f"Error uploading image: {str(e)}")
                
                # Append to existing images or replace
                existing_images = car.images.split(",") if car.images else []
                all_images = existing_images + new_image_urls
                update_data['images'] = ",".join(all_images)
            
            for key, value in update_data.items():
                setattr(car, key, value)
            
            db.commit()
            db.refresh(car)
            
            logger.info(f"Car updated: {car.id}")
            return car
            
        except Exception as e:
            logger.error(f"Error updating car: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def delete_car(db: Session, car_id: int) -> bool:
        """Delete a car"""
        try:
            car = db.query(Cars).filter(Cars.id == car_id).first()
            if not car:
                return False
            
            db.delete(car)
            db.commit()
            logger.info(f"Car deleted: {car_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting car: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    def get_car(db: Session, car_id: int) -> Optional[Cars]:
        """Get car by ID"""
        return db.query(Cars).filter(Cars.id == car_id).first()
    
    @staticmethod
    def get_cars(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
        car_type: Optional[CarType] = None,
        search: Optional[str] = None
    ) -> List[Cars]:
        """Get list of cars, ordered by latest first"""
        query = db.query(Cars)
        
        if active_only:
            query = query.filter(Cars.active == True)
        
        if car_type:
            query = query.filter(Cars.car_type == car_type)
        
        if search:
            like_pattern = f"%{search}%"
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Cars.registration_number.ilike(like_pattern),
                    Cars.brand.ilike(like_pattern),
                    Cars.car_model.ilike(like_pattern)
                )
            )
        
        # Order by latest first (by id desc, as id is auto-incrementing)
        return query.order_by(Cars.id.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def toggle_car_active(db: Session, car_id: int) -> Optional[Cars]:
        """Toggle car active status"""
        car = db.query(Cars).filter(Cars.id == car_id).first()
        if not car:
            return None
        
        car.active = not car.active
        db.commit()
        db.refresh(car)
        return car
    
    @staticmethod
    def block_car_availability(
        db: Session,
        car_id: int,
        availability_data: CarAvailabilityCreate,
        created_by: int
    ) -> CarAvailability:
        """Block car availability for a period"""
        availability = CarAvailability(
            car_id=car_id,
            start_date=availability_data.start_date,
            end_date=availability_data.end_date,
            reason=availability_data.reason,
            description=availability_data.description,
            created_by=created_by
        )
        
        db.add(availability)
        db.commit()
        db.refresh(availability)
        
        return availability
    
    @staticmethod
    def get_car_availability(db: Session, car_id: int) -> List[CarAvailability]:
        """Get availability blocks for a car"""
        return db.query(CarAvailability).filter(
            CarAvailability.car_id == car_id
        ).all()
    
    @staticmethod
    def is_car_available(
        db: Session,
        car_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> bool:
        """Check if car is available for given period"""
        # Check active status
        car = db.query(Cars).filter(Cars.id == car_id).first()
        if not car or not car.active:
            return False
        
        # Check availability blocks
        conflicts = db.query(CarAvailability).filter(
            and_(
                CarAvailability.car_id == car_id,
                or_(
                    and_(
                        CarAvailability.start_date <= start_date,
                        CarAvailability.end_date >= start_date
                    ),
                    and_(
                        CarAvailability.start_date <= end_date,
                        CarAvailability.end_date >= end_date
                    ),
                    and_(
                        CarAvailability.start_date >= start_date,
                        CarAvailability.end_date <= end_date
                    )
                )
            )
        ).first()
        
        return conflicts is None


# Global instance
car_service = CarService()

