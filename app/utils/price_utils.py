"""
Price calculation utilities
"""
from typing import Dict, Any, Optional, Tuple
from app.db.models import Cars
from app.core.logging_config import logger


def calculate_price(
    days: int, 
    hours: int, 
    car: Cars,
    discount_amount: Optional[float] = None
) -> Tuple[float, float, float, float]:
    """
    Calculate total price, advance amount, pay at car amount, and discount
    
    Args:
        days: Number of days
        hours: Number of hours
        car: Car object with pricing information
        discount_amount: Optional discount amount to apply
        
    Returns:
        Tuple of (total_amount, advance_amount, pay_at_car, discount_applied)
    """
    try:
        # Get price based on days
        price = car.base_price
        if car.prices:
            for day_range, day_price in car.prices.items():
                starting_day, ending_day = day_range.split('-')
                starting_day = int(starting_day)
                ending_day = int(ending_day)
                if starting_day <= days <= ending_day:
                    price = day_price
                    break
        
        price = int(price)
        
        # Calculate total price for days and hours
        total_amount = days * price + (price / 24) * hours
        total_amount = round(total_amount, 2)
        
        # Add protection price
        total_amount = total_amount + car.protection_price
        
        # Apply discount if provided
        discount_applied = 0.0
        if discount_amount:
            discount_applied = min(discount_amount, total_amount)  # Don't exceed total
            total_amount = total_amount - discount_applied
            total_amount = max(0, round(total_amount, 2))  # Ensure non-negative
        
        # Calculate 30% of the discounted total amount as advance_amount
        advance_amount = round(total_amount * 0.3, 2)
        pay_at_car = total_amount - advance_amount
        
        logger.info(
            f"Price calculated: days={days}, hours={hours}, "
            f"total={total_amount}, advance={advance_amount}, pay_at_car={pay_at_car}, "
            f"discount={discount_applied}"
        )
        
        return total_amount, advance_amount, pay_at_car, discount_applied
        
    except Exception as e:
        logger.error(f"Error calculating price: {str(e)}")
        raise


def get_insurance_prices(days: int) -> list[int]:
    """
    Get insurance prices based on number of days
    
    Args:
        days: Number of days
        
    Returns:
        List of insurance prices [0, basic, premium]
    """
    if 0 < days <= 10:
        return [0, 250, 350]
    else:
        return [0, 200, 300]

