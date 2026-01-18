"""
Payment calculation service
Handles pricing breakdown, protection fee, GST, and total calculation
"""
from typing import Dict, Optional
from datetime import datetime

from app.core.logging_config import logger


class PaymentCalculationService:
    """Service for payment calculations"""
    
    GST_RATE = 0.18  # 18% GST
    
    @staticmethod
    def calculate_rental_price(
        base_price: float,
        hours: int
    ) -> float:
        """
        Calculate base rental price
        
        Args:
            base_price: Hourly price per hour
            hours: Number of hours
            
        Returns:
            Base rental price
        """
        return base_price * max(1, hours)
    
    @staticmethod
    def calculate_protection_fee(
        damage_protection: int
    ) -> float:
        """
        Calculate damage protection fee based on selected protection level
        
        Args:
            damage_protection: Protection level (0, 277, or 477)
            
        Returns:
            Protection fee amount
        """
        # Protection fee is the selected amount (0, 277, or 477)
        return float(damage_protection)
    
    @staticmethod
    def calculate_gst(
        base_rental: float,
        protection_fee: float
    ) -> float:
        """
        Calculate GST (18% on rental + protection)
        
        Args:
            base_rental: Base rental amount
            protection_fee: Protection fee
            
        Returns:
            GST amount
        """
        taxable_amount = base_rental + protection_fee
        return taxable_amount * PaymentCalculationService.GST_RATE
    
    @staticmethod
    def calculate_total(
        base_rental: float,
        protection_fee: float,
        gst: float,
        deposit: float = 0.0,
        other_charges: float = 0.0
    ) -> float:
        """
        Calculate total payable amount
        
        Args:
            base_rental: Base rental amount
            protection_fee: Protection fee
            gst: GST amount
            deposit: Deposit amount (refundable, separate from total)
            other_charges: Other charges (cleaning, etc.)
            
        Returns:
            Total payable amount
        """
        return base_rental + protection_fee + gst + other_charges
    
    @staticmethod
    def get_damage_liability(
        damage_protection: int,
        damage_amount: float
    ) -> float:
        """
        Get damage liability amount based on protection level and damage amount
        
        Args:
            damage_protection: Protection level (0, 277, or 477)
            damage_amount: Actual damage amount
            
        Returns:
            Damage liability amount based on protection level:
            - 0: Full amount (minimum ₹5000 for any damage)
            - 277: 70% of damage amount
            - 477: 50% of damage amount
        """
        if damage_protection == 0:
            # Pay full amount, minimum ₹5000 for any damage
            return max(5000.0, damage_amount)
        elif damage_protection == 277:
            # Pay 70% of damage amount
            return damage_amount * 0.7
        elif damage_protection == 477:
            # Pay 50% of damage amount
            return damage_amount * 0.5
        else:
            # Default: full amount
            return max(5000.0, damage_amount)
    
    @staticmethod
    def calculate_pricing_breakdown(
        base_price: float,
        damage_price: float,
        hours: int,
        damage_protection: int = 0,
        deposit: float = 0.0,
        other_charges: float = 0.0,
        discount_amount: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate complete pricing breakdown
        
        Args:
            base_price: Hourly price per hour
            damage_price: Maximum damage price (for liability calculation reference)
            hours: Number of hours
            damage_protection: Protection level (0, 277, or 477)
            deposit: Deposit amount (refundable)
            other_charges: Other charges
            discount_amount: Optional discount amount from coupon
            
        Returns:
            Dictionary with all pricing components
        """
        try:
            base_rental = PaymentCalculationService.calculate_rental_price(base_price, hours)
            protection_fee = PaymentCalculationService.calculate_protection_fee(damage_protection)
            
            # Calculate subtotal before discount
            subtotal_before_discount = base_rental + protection_fee + other_charges
            
            # Apply discount if provided
            discount_applied = 0.0
            if discount_amount:
                discount_applied = min(discount_amount, subtotal_before_discount)
                subtotal_after_discount = subtotal_before_discount - discount_applied
            else:
                subtotal_after_discount = subtotal_before_discount
            
            # GST is calculated on the discounted amount (base_rental + protection_fee after discount)
            # Calculate GST on the subtotal after discount
            gst = subtotal_after_discount * PaymentCalculationService.GST_RATE
            
            total = subtotal_after_discount + gst
            
            # Calculate damage liability (using max damage price as reference)
            # This shows what the liability would be for maximum damage
            damage_liability = PaymentCalculationService.get_damage_liability(
                damage_protection, damage_price
            )
            
            return {
                "base_rental": round(base_rental, 2),
                "protection_fee": round(protection_fee, 2),
                "gst": round(gst, 2),
                "other_charges": round(other_charges, 2),
                "subtotal": round(subtotal_after_discount, 2),
                "discount": round(discount_applied, 2),
                "total": round(total, 2),
                "deposit": round(deposit, 2),
                "damage_liability": round(damage_liability, 2),
                "hours": hours
            }
        except Exception as e:
            logger.error(f"Error calculating pricing breakdown: {str(e)}")
            raise


# Global instance
payment_calculation_service = PaymentCalculationService()

