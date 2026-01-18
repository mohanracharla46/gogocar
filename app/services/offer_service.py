"""
Offer/Coupon service for validation and discount calculation
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import Coupons, Orders, Cars
from app.core.logging_config import logger


class OfferService:
    """Service for offer/coupon operations"""
    
    @staticmethod
    def validate_coupon(
        db: Session,
        coupon_code: str,
        user_id: int,
        car_id: int,
        total_amount: float
    ) -> Dict[str, Any]:
        """
        Validate a coupon code and return discount information
        
        Args:
            db: Database session
            coupon_code: Coupon code to validate
            user_id: User ID applying the coupon
            car_id: Car ID for the booking
            total_amount: Total booking amount before discount
            
        Returns:
            Dict with validation result and discount details
        """
        try:
            # Find coupon
            coupon = db.query(Coupons).filter(
                Coupons.coupon_code == coupon_code.upper().strip()
            ).first()
            
            if not coupon:
                return {
                    "valid": False,
                    "error": "Invalid coupon code"
                }
            
            # Check if coupon is active
            if not coupon.is_active:
                return {
                    "valid": False,
                    "error": "This coupon is no longer active"
                }
            
            # Check expiration
            if coupon.expiration_time < datetime.now():
                return {
                    "valid": False,
                    "error": "This coupon has expired"
                }
            
            # Check usage limit
            if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
                return {
                    "valid": False,
                    "error": "This coupon has reached its usage limit"
                }
            
            # Check minimum amount
            if coupon.min_amount and total_amount < coupon.min_amount:
                return {
                    "valid": False,
                    "error": f"Minimum order amount of ₹{coupon.min_amount} required"
                }
            
            # Check car type restrictions
            if coupon.applicable_to_car_type:
                car = db.query(Cars).filter(Cars.id == car_id).first()
                if car and car.car_type.value not in coupon.applicable_to_car_type:
                    return {
                        "valid": False,
                        "error": f"This coupon is not applicable to {car.car_type.value} cars"
                    }
            
            # Check specific car restrictions
            if coupon.applicable_to_car_ids:
                if car_id not in coupon.applicable_to_car_ids:
                    return {
                        "valid": False,
                        "error": "This coupon is not applicable to this car"
                    }
            
            # Calculate discount
            discount_amount = 0
            if coupon.discount_type == "PERCENTAGE":
                discount_amount = (total_amount * coupon.discount) / 100
                # Apply max discount if set
                if coupon.max_discount and discount_amount > coupon.max_discount:
                    discount_amount = coupon.max_discount
            else:  # FIXED
                discount_amount = coupon.discount
                # Ensure discount doesn't exceed total amount
                if discount_amount > total_amount:
                    discount_amount = total_amount
            
            final_amount = total_amount - discount_amount
            
            return {
                "valid": True,
                "coupon_id": coupon.id,
                "coupon_code": coupon.coupon_code,
                "discount_type": coupon.discount_type,
                "discount_amount": round(discount_amount, 2),
                "original_amount": round(total_amount, 2),
                "final_amount": round(final_amount, 2),
                "description": coupon.description
            }
            
        except Exception as e:
            logger.error(f"Error validating coupon: {str(e)}")
            return {
                "valid": False,
                "error": "An error occurred while validating the coupon"
            }
    
    @staticmethod
    def apply_coupon(db: Session, coupon_id: int) -> bool:
        """
        Increment coupon usage count when applied to an order
        
        Args:
            db: Database session
            coupon_id: Coupon ID to apply
            
        Returns:
            True if successful, False otherwise
        """
        try:
            coupon = db.query(Coupons).filter(Coupons.id == coupon_id).first()
            if coupon:
                coupon.usage_count += 1
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error applying coupon: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    def get_coupon_usage_count(db: Session, coupon_id: int) -> int:
        """Get current usage count for a coupon"""
        coupon = db.query(Coupons).filter(Coupons.id == coupon_id).first()
        if coupon:
            return coupon.usage_count
        return 0


# Global instance
offer_service = OfferService()

