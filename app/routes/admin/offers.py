"""
Admin API routes for offers/coupons management
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.db.models import Coupons
from app.routes.admin.dependencies import require_admin
from app.schemas.offer import OfferCreate, OfferUpdate, OfferResponse
from app.core.logging_config import logger
from app.utils.pagination import paginate_query, PaginatedResponse


router = APIRouter(
    prefix="/admin/api/offers",
    tags=["admin-offers"]
)


def enrich_offer(coupon: Coupons) -> dict:
    """Enrich coupon data for response"""
    return {
        "id": coupon.id,
        "coupon_code": coupon.coupon_code,
        "discount": coupon.discount,
        "discount_type": coupon.discount_type,
        "is_active": coupon.is_active,
        "expiration_time": coupon.expiration_time,
        "usage_limit": coupon.usage_limit,
        "usage_count": coupon.usage_count,
        "min_amount": coupon.min_amount,
        "max_discount": coupon.max_discount,
        "applicable_to_car_type": coupon.applicable_to_car_type,
        "applicable_to_car_ids": coupon.applicable_to_car_ids,
        "description": coupon.description,
        "created_at": coupon.created_at,
        "updated_at": coupon.updated_at
    }


@router.get("", response_model=PaginatedResponse)
async def list_offers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all offers with pagination and filters"""
    try:
        query = db.query(Coupons)
        
        # Search filter
        if search:
            query = query.filter(
                or_(
                    Coupons.coupon_code.ilike(f"%{search}%"),
                    Coupons.description.ilike(f"%{search}%")
                )
            )
        
        # Active filter
        if is_active is not None:
            query = query.filter(Coupons.is_active == is_active)
        
        # Order by latest first
        query = query.order_by(Coupons.created_at.desc())
        
        # Paginate
        offers, pagination = paginate_query(query, page=page, page_size=page_size)
        
        # Enrich data
        items = [enrich_offer(offer) for offer in offers]
        
        return PaginatedResponse(
            items=items,
            total=pagination.total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=pagination.total_pages,
            has_next=pagination.has_next,
            has_prev=pagination.has_prev
        )
    except Exception as e:
        logger.error(f"Error listing offers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list offers"
        )


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get a single offer by ID"""
    offer = db.query(Coupons).filter(Coupons.id == offer_id).first()
    
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found"
        )
    
    return OfferResponse(**enrich_offer(offer))


@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    offer_data: OfferCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create a new offer"""
    try:
        # Check if coupon code already exists
        existing = db.query(Coupons).filter(
            Coupons.coupon_code == offer_data.coupon_code.upper().strip()
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coupon code already exists"
            )
        
        # Create new coupon
        coupon = Coupons(
            coupon_code=offer_data.coupon_code.upper().strip(),
            discount=offer_data.discount,
            discount_type=offer_data.discount_type.upper(),
            is_active=offer_data.is_active,
            expiration_time=offer_data.expiration_time,
            usage_limit=offer_data.usage_limit,
            usage_count=0,
            min_amount=offer_data.min_amount,
            max_discount=offer_data.max_discount,
            applicable_to_car_type=offer_data.applicable_to_car_type,
            applicable_to_car_ids=offer_data.applicable_to_car_ids,
            description=offer_data.description
        )
        
        db.add(coupon)
        db.commit()
        db.refresh(coupon)
        
        logger.info(f"Offer created: {coupon.coupon_code} by admin {current_user['user_id']}")
        
        return OfferResponse(**enrich_offer(coupon))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating offer: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create offer"
        )


@router.put("/{offer_id}", response_model=OfferResponse)
async def update_offer(
    offer_id: int,
    offer_data: OfferUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update an existing offer"""
    try:
        coupon = db.query(Coupons).filter(Coupons.id == offer_id).first()
        
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offer not found"
            )
        
        # Check coupon code uniqueness if being updated
        if offer_data.coupon_code and offer_data.coupon_code.upper().strip() != coupon.coupon_code:
            existing = db.query(Coupons).filter(
                Coupons.coupon_code == offer_data.coupon_code.upper().strip(),
                Coupons.id != offer_id
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Coupon code already exists"
                )
        
        # Update fields
        update_dict = offer_data.model_dump(exclude_unset=True)
        
        for key, value in update_dict.items():
            if key == "coupon_code":
                setattr(coupon, key, value.upper().strip())
            elif key == "discount_type":
                setattr(coupon, key, value.upper())
            else:
                setattr(coupon, key, value)
        
        db.commit()
        db.refresh(coupon)
        
        logger.info(f"Offer updated: {coupon.coupon_code} by admin {current_user['user_id']}")
        
        return OfferResponse(**enrich_offer(coupon))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating offer: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update offer"
        )


@router.delete("/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Delete an offer"""
    try:
        coupon = db.query(Coupons).filter(Coupons.id == offer_id).first()
        
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offer not found"
            )
        
        db.delete(coupon)
        db.commit()
        
        logger.info(f"Offer deleted: {coupon.coupon_code} by admin {current_user['user_id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting offer: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete offer"
        )


@router.post("/{offer_id}/toggle", response_model=OfferResponse)
async def toggle_offer_status(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Toggle offer active status"""
    try:
        coupon = db.query(Coupons).filter(Coupons.id == offer_id).first()
        
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offer not found"
            )
        
        coupon.is_active = not coupon.is_active
        db.commit()
        db.refresh(coupon)
        
        logger.info(f"Offer status toggled: {coupon.coupon_code} to {coupon.is_active} by admin {current_user['user_id']}")
        
        return OfferResponse(**enrich_offer(coupon))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling offer status: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle offer status"
        )

