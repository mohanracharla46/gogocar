"""
Location management service
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.models import Location
from app.schemas.location import LocationCreate, LocationUpdate
from app.core.logging_config import logger


class LocationService:
    """Service for location management operations"""
    
    @staticmethod
    def create_location(db: Session, location_data: LocationCreate) -> Location:
        """
        Create a new location
        
        Args:
            db: Database session
            location_data: Location creation data
            
        Returns:
            Created location object
        """
        try:
            # Check if location already exists
            existing = db.query(Location).filter(
                Location.location == location_data.location
            ).first()
            
            if existing:
                raise ValueError(f"Location '{location_data.location}' already exists")
            
            location = Location(
                location=location_data.location,
                maps_link=location_data.maps_link
            )
            db.add(location)
            db.commit()
            db.refresh(location)
            
            logger.info(f"Location created: {location.id} - {location.location}")
            return location
            
        except Exception as e:
            logger.error(f"Error creating location: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def update_location(
        db: Session,
        location_id: int,
        location_data: LocationUpdate
    ) -> Optional[Location]:
        """
        Update an existing location
        
        Args:
            db: Database session
            location_id: Location ID
            location_data: Location update data
            
        Returns:
            Updated location object or None
        """
        try:
            location = db.query(Location).filter(Location.id == location_id).first()
            if not location:
                return None
            
            update_data = location_data.dict(exclude_unset=True)
            
            # Check if new location name already exists
            if 'location' in update_data:
                existing = db.query(Location).filter(
                    Location.location == update_data['location'],
                    Location.id != location_id
                ).first()
                
                if existing:
                    raise ValueError(f"Location '{update_data['location']}' already exists")
            
            for key, value in update_data.items():
                setattr(location, key, value)
            
            db.commit()
            db.refresh(location)
            
            logger.info(f"Location updated: {location_id}")
            return location
            
        except Exception as e:
            logger.error(f"Error updating location: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def delete_location(db: Session, location_id: int) -> bool:
        """Delete a location"""
        try:
            location = db.query(Location).filter(Location.id == location_id).first()
            if not location:
                return False
            
            # Check if location is in use by any cars
            from app.db.models import Cars
            cars_using_location = db.query(Cars).filter(
                Cars.location_id == location_id
            ).count()
            
            if cars_using_location > 0:
                raise ValueError(f"Cannot delete location: {cars_using_location} car(s) are using this location")
            
            db.delete(location)
            db.commit()
            logger.info(f"Location deleted: {location_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting location: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def get_location(db: Session, location_id: int) -> Optional[Location]:
        """Get location by ID"""
        return db.query(Location).filter(Location.id == location_id).first()
    
    @staticmethod
    def get_locations(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Location]:
        """Get list of locations, ordered by latest first"""
        return db.query(Location).order_by(Location.id.desc()).offset(skip).limit(limit).all()


# Global instance
location_service = LocationService()

