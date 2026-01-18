"""
Booking routes for order management and payment integration
"""
from typing import List, Optional
from datetime import datetime
import uuid
from fastapi import (
    APIRouter, Depends, File, HTTPException, Request,
    UploadFile, status, Form
)
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, not_

from app.db.session import get_db
from app.db.models import (
    Orders, UserProfile, PaymentStatus, TempOrders
)
from app.routes.auth import get_current_user
from app.services.ccavenue_service import ccavenue_service
from app.core.logging_config import logger
from app.core.config import settings
from app.core.templates import templates
from app.utils.file_utils import upload_file_to_s3
from typing import Optional

router = APIRouter(
    prefix="/orders",
    tags=["bookings"]
)


@router.get("/view", status_code=status.HTTP_200_OK)
def view_orders(
    request: Request,
    page: int = 1,
    page_size: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    View user's orders with pagination
    
    Args:
        request: FastAPI request object
        page: Page number (default: 1)
        page_size: Items per page (default: 10)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Template response with paginated orders list
    """
    if current_user.get("error"):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        from app.utils.pagination import paginate_query
        
        user = db.query(UserProfile).filter(
            UserProfile.id == current_user["user_id"]
        ).first()
        
        # Build query with car relationship loaded
        from sqlalchemy.orm import joinedload
        from app.db.models import Cars, Reviews
        query = db.query(Orders).options(
            joinedload(Orders.car)
        ).filter(
            Orders.user_id == user.id
        ).order_by(Orders.id.desc())
        
        # Validate and limit page_size
        page_size = min(max(1, page_size), 100)  # Between 1 and 100
        
        # Paginate
        orders, pagination = paginate_query(query, page=page, page_size=page_size)
        
        # Get review status for each order
        order_review_status = {}
        for order in orders:
            if order.order_status.value == "COMPLETED":
                existing_review = db.query(Reviews).filter(
                    Reviews.order_id == order.id,
                    Reviews.user_id == user.id
                ).first()
                order_review_status[order.id] = {
                    "can_review": existing_review is None,
                    "has_review": existing_review is not None
                }
        
        return templates.TemplateResponse(
            "orders/orders_list.html",
            {
                "request": request,
                "orders": orders,
                "pagination": pagination,
                "user": user,
                "order_review_status": order_review_status
            }
        )
    except Exception as e:
        logger.error(f"Error viewing orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load orders"
        )


@router.get("/detail/{order_id}", status_code=status.HTTP_200_OK)
def view_order_detail(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    View order details
    
    Args:
        request: FastAPI request object
        order_id: Order ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Template response with order details
    """
    if current_user.get("error"):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        user = db.query(UserProfile).filter(
            UserProfile.id == current_user["user_id"]
        ).first()
        
        # Get order with relationships
        from sqlalchemy.orm import joinedload
        from app.db.models import Cars, Location
        order = db.query(Orders).options(
            joinedload(Orders.car).joinedload(Cars.location)
        ).filter(
            Orders.id == order_id,
            Orders.user_id == user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Check if review already exists for this order
        from app.db.models import Reviews
        existing_review = db.query(Reviews).filter(
            Reviews.order_id == order_id,
            Reviews.user_id == user.id
        ).first()
        
        can_review = (
            order.order_status.value == "COMPLETED" and 
            existing_review is None
        )
        
        return templates.TemplateResponse(
            "orders/order_detail.html",
            {
                "request": request,
                "order": order,
                "user": user,
                "can_review": can_review,
                "existing_review": existing_review
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing order detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load order details"
        )


@router.get("/list/view", status_code=status.HTTP_200_OK)
def view_orders_admin(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    View all orders (admin)
    
    Args:
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Template response with all orders
    """
    if current_user.get("error") or not current_user.get("isadmin"):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        orders = db.query(Orders).order_by(Orders.id.desc()).all()
        
        return templates.TemplateResponse(
            "admin/orders/vieworders.html",
            {"request": request, "orders": orders}
        )
    except Exception as e:
        logger.error(f"Error viewing orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load orders"
        )


@router.post("/checkout")
async def checkout_order(
    request: Request,
    db: Session = Depends(get_db),
    order_id: int = Form(...),
    phone: str = Form(...),
    aadhaar_front: Optional[UploadFile] = File(None),
    aadhaar_back: Optional[UploadFile] = File(None),
    drivinglicense_front: Optional[UploadFile] = File(None),
    drivinglicense_back: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Checkout order and upload documents
    
    Args:
        request: FastAPI request object
        db: Database session
        order_id: Temporary order ID
        phone: User phone number
        aadhaar_front: Aadhaar front image
        aadhaar_back: Aadhaar back image
        drivinglicense_front: Driving license front image
        drivinglicense_back: Driving license back image
        current_user: Current authenticated user
        
    Returns:
        Template response with payment page
    """
    if current_user.get("error"):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        user = db.query(UserProfile).filter(
            UserProfile.id == current_user["user_id"]
        ).first()
        
        # Update user phone if not set
        if not user.phone:
            user.phone = phone
        
        # Upload documents if provided
        if aadhaar_front and not user.aadhaar_front:
            aadhaar_front.filename = f"{uuid.uuid4()}.jpg"
            contents = await aadhaar_front.read()
            with open(f"{settings.IMAGE_DIR}{aadhaar_front.filename}", 'wb') as f:
                f.write(contents)
                aadhaar_front_url = upload_file_to_s3(
                    filepath=f.name,
                    bucket_name=settings.S3_BUCKET_NAME,
                    object_name=aadhaar_front.filename
                )
                user.aadhaar_front = aadhaar_front_url
        
        if aadhaar_back and not user.aadhaar_back:
            aadhaar_back.filename = f"{uuid.uuid4()}.jpg"
            contents = await aadhaar_back.read()
            with open(f"{settings.IMAGE_DIR}{aadhaar_back.filename}", 'wb') as f:
                f.write(contents)
                aadhaar_back_url = upload_file_to_s3(
                    filepath=f.name,
                    bucket_name=settings.S3_BUCKET_NAME,
                    object_name=aadhaar_back.filename
                )
                user.aadhaar_back = aadhaar_back_url
        
        if drivinglicense_front and not user.drivinglicense_front:
            drivinglicense_front.filename = f"{uuid.uuid4()}.jpg"
            contents = await drivinglicense_front.read()
            with open(f"{settings.IMAGE_DIR}{drivinglicense_front.filename}", 'wb') as f:
                f.write(contents)
                drivinglicense_front_url = upload_file_to_s3(
                    filepath=f.name,
                    bucket_name=settings.S3_BUCKET_NAME,
                    object_name=drivinglicense_front.filename
                )
                user.drivinglicense_front = drivinglicense_front_url
        
        if drivinglicense_back and not user.drivinglicense_back:
            drivinglicense_back.filename = f"{uuid.uuid4()}.jpg"
            contents = await drivinglicense_back.read()
            with open(f"{settings.IMAGE_DIR}{drivinglicense_back.filename}", 'wb') as f:
                f.write(contents)
                drivinglicense_back_url = upload_file_to_s3(
                    filepath=f.name,
                    bucket_name=settings.S3_BUCKET_NAME,
                    object_name=drivinglicense_back.filename
                )
                user.drivinglicense_back = drivinglicense_back_url
        
        db.add(user)
        db.commit()
        
        # Get temporary order
        temp_order = db.query(TempOrders).filter(
            TempOrders.id == order_id
        ).first()
        
        if not temp_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Render payment page with order details
        # The payment page will have a "Pay Now" button that initiates CCAvenue payment
        return templates.TemplateResponse(
            "orders/payment.html",
            {
                "request": request,
                "user": user,
                "order": temp_order
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in checkout: {str(e)}")
        return templates.TemplateResponse(
            "orders/order_detail_page.html",
            {"request": request, "user": user, "msg": "Please provide valid information"}
        )


@router.post("/create")
def create_order(
    order_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create order in database
    
    Args:
        order_data: Order data dictionary
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary with order information
    """
    if current_user.get("error"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    try:
        # Create order in database
        new_order = Orders(
            user_id=order_data["user_id"],
            car_id=order_data["car_id"],
            start_time=order_data["start_time"],
            end_time=order_data["end_time"],
            pay_advance_amount=order_data["pay_advance_amount"],
            pay_at_car=order_data["pay_at_car"],
            advance_amount_status=PaymentStatus.INITIATED
        )
        
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        
        logger.info(f"Order created: {new_order.id}")
        
        # Return order information for payment initiation
        return {
            "order_id": new_order.id,
            "amount": new_order.pay_advance_amount,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


@router.get("/{order_id}")
def read_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Get order by ID
    
    Args:
        order_id: Order ID
        db: Database session
        
    Returns:
        Order object
    """
    order = db.query(Orders).filter(Orders.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order


@router.put("/update/{order_id}")
def update_order(
    order_id: str,
    order_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update order (deprecated - use payment callback instead)
    
    Args:
        order_id: Order ID
        order_data: Order update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    if current_user.get("error"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    db_order = db.query(Orders).filter(Orders.order_id == order_id).first()
    
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update order status (payment callback handles this now)
    if order_data.get("advance_amount_status") == "FAILED":
        db_order.advance_amount_status = PaymentStatus.FAILED
        db_order.payment_error_code = order_data.get("payment_error_code")
        db_order.payment_description = order_data.get("payment_description")
        db_order.error_reason = order_data.get("error_reason")
        
        db.add(db_order)
        db.commit()
        
        logger.info(f"Order {order_id} updated to FAILED")
    
    return {"success": "Order updated successfully", "status_code": 200}


@router.delete("/delete/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete order
    
    Args:
        order_id: Order ID
        db: Database session
        
    Returns:
        Deleted order
    """
    order = db.query(Orders).filter(Orders.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    db.delete(order)
    db.commit()
    
    logger.info(f"Order {order_id} deleted")
    return order


@router.get("/")
def read_orders(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get paginated orders list
    
    Args:
        skip: Number of records to skip
        limit: Number of records to return
        db: Database session
        
    Returns:
        Dictionary with orders list
    """
    orders = db.query(Orders).offset(skip).limit(limit).all()
    return {"items": orders}

