"""
Admin routes for location management
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.services.location_service import location_service
from app.routes.admin.dependencies import require_admin
from app.utils.pagination import paginate_query, PaginatedResponse
from app.core.logging_config import logger

router = APIRouter(
    prefix="/admin/api/locations",  # API routes under /admin/api
    tags=["admin-locations"]
)


@router.get("", response_model=PaginatedResponse[LocationResponse])
async def list_locations(
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all locations with pagination"""
    skip = (page - 1) * page_size
    
    locations = location_service.get_locations(
        db=db,
        skip=skip,
        limit=page_size
    )
    
    # Get total count for pagination
    from app.db.models import Location
    total = db.query(Location).count()
    
    return PaginatedResponse(
        items=locations,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
        has_next=page * page_size < total,
        has_prev=page > 1
    )


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get location by ID"""
    location = location_service.get_location(db, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_data: LocationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create a new location"""
    try:
        location = location_service.create_location(db, location_data)
        return location
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating location: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating location")


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: int,
    location_data: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update a location"""
    try:
        location = location_service.update_location(db, location_id, location_data)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        return location
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating location: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating location")


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Delete a location"""
    try:
        success = location_service.delete_location(db, location_id)
        if not success:
            raise HTTPException(status_code=404, detail="Location not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting location: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

