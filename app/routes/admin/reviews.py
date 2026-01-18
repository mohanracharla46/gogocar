"""
Admin routes for managing reviews
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.db.models import Reviews, UserProfile, Cars
from app.routes.admin.dependencies import require_admin
from app.schemas.review import ReviewResponse, ReviewUpdate
from app.utils.pagination import PaginatedResponse, paginate_query
from app.core.logging_config import logger

router = APIRouter(
    prefix="/admin/api/reviews",
    tags=["admin-reviews"]
)


@router.get("", response_model=PaginatedResponse[ReviewResponse])
async def list_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    List all reviews with pagination
    
    Args:
        page: Page number
        page_size: Items per page
        db: Database session
        current_user: Current admin user
        
    Returns:
        Paginated list of reviews
    """
    query = db.query(Reviews).options(
        joinedload(Reviews.user),
        joinedload(Reviews.car)
    ).order_by(Reviews.created_at.desc())
    
    reviews, pagination = paginate_query(query, page=page, page_size=page_size)
    
    # Enrich reviews with user and car details
    enriched_reviews = []
    for review in reviews:
        # Create base response from model
        review_data = ReviewResponse.model_validate(review)
        
        # Add enriched fields
        review_dict = review_data.model_dump()
        review_dict["user_firstname"] = review.user.firstname if review.user else None
        review_dict["user_lastname"] = review.user.lastname if review.user else None
        review_dict["car_brand"] = review.car.brand if review.car else None
        review_dict["car_model"] = review.car.car_model if review.car else None
        
        enriched_reviews.append(ReviewResponse(**review_dict))
    
    return PaginatedResponse(
        items=enriched_reviews,
        total=pagination.total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=pagination.total_pages,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Get a single review
    
    Args:
        review_id: Review ID
        db: Database session
        current_user: Current admin user
        
    Returns:
        Review details
    """
    review = db.query(Reviews).options(
        joinedload(Reviews.user),
        joinedload(Reviews.car)
    ).filter(Reviews.id == review_id).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Create base response from model
    review_data = ReviewResponse.model_validate(review)
    
    # Add enriched fields
    review_dict = review_data.model_dump()
    review_dict["user_firstname"] = review.user.firstname if review.user else None
    review_dict["user_lastname"] = review.user.lastname if review.user else None
    review_dict["car_brand"] = review.car.brand if review.car else None
    review_dict["car_model"] = review.car.car_model if review.car else None
    
    return ReviewResponse(**review_dict)


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Update review (approve/hide)
    
    Args:
        review_id: Review ID
        review_data: Review update data
        db: Database session
        current_user: Current admin user
        
    Returns:
        Updated review
    """
    review = db.query(Reviews).filter(Reviews.id == review_id).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    update_data = review_data.dict(exclude_unset=True)
    
    # Update is_approved
    if 'is_approved' in update_data:
        review.is_approved = update_data['is_approved']
        if update_data['is_approved']:
            from datetime import datetime
            review.approved_by = current_user["user_id"]
            review.approved_at = datetime.now()
        else:
            review.approved_by = None
            review.approved_at = None
    
    # Update is_hidden
    if 'is_hidden' in update_data:
        review.is_hidden = update_data['is_hidden']
    
    db.commit()
    db.refresh(review)
    
    # Reload relationships
    review = db.query(Reviews).options(
        joinedload(Reviews.user),
        joinedload(Reviews.car)
    ).filter(Reviews.id == review_id).first()
    
    logger.info(f"Review {review_id} updated by admin {current_user['user_id']}")
    
    # Create base response from model
    review_data = ReviewResponse.model_validate(review)
    
    # Add enriched fields
    review_dict = review_data.model_dump()
    review_dict["user_firstname"] = review.user.firstname if review.user else None
    review_dict["user_lastname"] = review.user.lastname if review.user else None
    review_dict["car_brand"] = review.car.brand if review.car else None
    review_dict["car_model"] = review.car.car_model if review.car else None
    
    return ReviewResponse(**review_dict)


@router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Delete a review
    
    Args:
        review_id: Review ID
        db: Database session
        current_user: Current admin user
        
    Returns:
        Success message
    """
    review = db.query(Reviews).filter(Reviews.id == review_id).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    db.delete(review)
    db.commit()
    
    logger.info(f"Review {review_id} deleted by admin {current_user['user_id']}")
    
    return {"message": "Review deleted successfully"}

