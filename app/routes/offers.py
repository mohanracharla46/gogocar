"""
Customer-facing offer/coupon routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.routes.auth import get_current_user
from app.services.offer_service import offer_service
from app.core.logging_config import logger


router = APIRouter(
    prefix="/offers",
    tags=["offers"]
)


@router.post("/validate")
async def validate_coupon(
    coupon_code: str = Query(...),
    car_id: int = Query(...),
    total_amount: float = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Validate a coupon code for a customer
    
    Args:
        coupon_code: Coupon code to validate
        car_id: Car ID for the booking
        total_amount: Total booking amount before discount
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Validation result with discount details
    """
    if current_user.get("error"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        result = offer_service.validate_coupon(
            db=db,
            coupon_code=coupon_code,
            user_id=current_user["user_id"],
            car_id=car_id,
            total_amount=total_amount
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating coupon: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate coupon"
        )

