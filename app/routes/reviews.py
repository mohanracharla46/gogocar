"""
Review routes for customer reviews and ratings
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models import Reviews, Orders, Cars, BookingStatus, UserProfile
from app.routes.auth import get_current_user
from app.schemas.review import ReviewResponse, ReviewCreate
from app.core.logging_config import logger

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"]
)


@router.post("/", response_model=ReviewResponse)
async def create_review(
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a review for a completed order
    
    Args:
        review_data: Review data with order_id, rating, and optional review_text
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created review
    """
    if current_user.get("error"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    order_id = review_data.order_id
    rating = review_data.rating
    review_text = review_data.review_text
    
    # Get order and verify it belongs to user and is completed
    order = db.query(Orders).filter(
        Orders.id == order_id,
        Orders.user_id == user_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.order_status != BookingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only review completed orders"
        )
    
    # Check if review already exists for this order
    existing_review = db.query(Reviews).filter(
        Reviews.order_id == order_id,
        Reviews.user_id == user_id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review already exists for this order"
        )
    
    # Create review - approved by default, admin can hide if needed
    from datetime import datetime
    
    # Get the first admin user to set as approver
    admin_user = db.query(UserProfile).filter(
        UserProfile.isadmin == True,
        UserProfile.is_active == True
    ).order_by(UserProfile.id.asc()).first()
    
    approved_by_id = admin_user.id if admin_user else None
    approved_at_time = datetime.now() if admin_user else None
    
    review = Reviews(
        car_id=order.car_id,
        user_id=user_id,
        order_id=order_id,
        rating=rating,
        review_text=review_text,
        is_approved=True,  # Approved by default
        is_hidden=False,   # Visible by default
        approved_by=approved_by_id,  # Set to first admin user ID
        approved_at=approved_at_time  # Set to current timestamp
    )
    
    db.add(review)
    db.commit()
    db.refresh(review)
    
    logger.info(f"Review created: {review.id} for order {order_id} by user {user_id}")
    
    return review


@router.get("/car/{car_id}", response_model=list[ReviewResponse])
async def get_car_reviews(
    car_id: int,
    approved_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get reviews for a car
    
    Args:
        car_id: Car ID
        approved_only: Only return approved and visible reviews
        db: Database session
        
    Returns:
        List of reviews
    """
    query = db.query(Reviews).filter(
        Reviews.car_id == car_id,
        Reviews.is_hidden == False  # Only show non-hidden reviews
    )
    
    if approved_only:
        query = query.filter(Reviews.is_approved == True)
    
    reviews = query.order_by(Reviews.created_at.desc()).all()
    return reviews


@router.get("/car/{car_id}/average-rating")
async def get_car_average_rating(
    car_id: int,
    db: Session = Depends(get_db)
):
    """
    Get average rating for a car
    
    Args:
        car_id: Car ID
        db: Database session
        
    Returns:
        Average rating and count
    """
    result = db.query(
        func.avg(Reviews.rating).label('avg_rating'),
        func.count(Reviews.id).label('review_count')
    ).filter(
        Reviews.car_id == car_id,
        Reviews.is_approved == True,  # Only approved reviews
        Reviews.is_hidden == False     # Only visible reviews
    ).first()
    
    avg_rating = float(result.avg_rating) if result.avg_rating else 0.0
    review_count = result.review_count or 0
    
    return {
        "average_rating": round(avg_rating, 1),
        "review_count": review_count,
        "car_id": car_id
    }

