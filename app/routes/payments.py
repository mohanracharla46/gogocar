"""
Payment routes for CCAvenue integration
"""
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.db.session import get_db
from app.db.models import Orders, UserProfile, PaymentStatus, BookingStatus, TempOrders
from app.services.ccavenue_service import ccavenue_service
from app.utils.email_service import email_service
from app.services.offer_service import offer_service
from app.core.logging_config import logger
from app.routes.auth import get_current_user
from app.core.config import settings

router = APIRouter(
    prefix="/payments",
    tags=["payments"]
)


@router.post("/calculate-price")
async def calculate_price(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate pricing breakdown securely from backend
    
    Args:
        request: FastAPI request object with JSON body
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        JSON response with pricing breakdown
    """
    try:
        if current_user.get("error"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        # Parse request body
        body = await request.json()
        car_id = body.get("car_id")
        hours = body.get("hours")
        damage_protection = body.get("damage_protection", 0)  # 0, 277, or 477
        coupon_code = body.get("coupon_code")
        
        if not car_id or not hours:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="car_id and hours are required"
            )
        
        # Validate damage_protection value
        if damage_protection not in [0, 277, 477]:
            damage_protection = 0  # Default to 0 if invalid
        
        # Get car from database
        from app.db.models import Cars
        car = db.query(Cars).filter(Cars.id == car_id).first()
        
        if not car:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Car not found"
            )
        
        # Calculate pricing using backend service
        from app.services.payment_calculation import payment_calculation_service
        
        # Validate coupon if provided
        discount_amount = None
        coupon_id = None
        if coupon_code:
            from app.services.offer_service import offer_service
            # Get subtotal for coupon validation
            base_rental = payment_calculation_service.calculate_rental_price(
                float(car.base_price), hours
            )
            protection_fee = payment_calculation_service.calculate_protection_fee(damage_protection)
            subtotal = base_rental + protection_fee
            
            coupon_result = offer_service.validate_coupon(
                db, coupon_code, car_id, subtotal
            )
            if coupon_result.get("valid"):
                discount_amount = coupon_result.get("discount_amount", 0)
                coupon_id = coupon_result.get("coupon_id")
        
        # Calculate pricing breakdown
        pricing_breakdown = payment_calculation_service.calculate_pricing_breakdown(
            base_price=float(car.base_price),
            damage_price=float(car.damage_price),
            hours=hours,
            damage_protection=damage_protection,
            deposit=float(car.prices.deposit) if car.prices and car.prices.deposit else 0.0,
            discount_amount=discount_amount
        )
        
        return {
            "success": True,
            "pricing": pricing_breakdown,
            "coupon_applied": coupon_id is not None,
            "coupon_id": coupon_id,
            "car": {
                "id": car.id,
                "base_price": float(car.base_price),
                "protection_price": float(car.protection_price),
                "damage_price": float(car.damage_price),
                "fuel_type": car.fuel_type.value if car.fuel_type else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating price: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate price"
        )


@router.post("/create-temp-order")
async def create_temp_order(
    request: Request,
    car_id: int = Form(...),
    pickup_datetime: str = Form(...),
    end_datetime: str = Form(...),
    hours: int = Form(...),
    damage_protection: int = Form(0),  # 0, 277, or 477
    deposit_type: str = Form("bike_rc"),  # bike_rc, laptop, cheque, cash
    base_rental: float = Form(...),
    discount: float = Form(0),
    total: float = Form(...),
    coupon_id: Optional[int] = Form(None),
    home_delivery: Optional[str] = Form("false"),
    delivery_address: Optional[str] = Form(None),
    delivery_latitude: Optional[str] = Form(None),
    delivery_longitude: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create temporary order from booking data
    
    Args:
        request: FastAPI request object
        car_id: Car ID
        pickup_datetime: Pickup datetime string
        end_datetime: End datetime string
        hours: Number of hours
        damage_protection: Damage protection level (0, 277, or 477)
        deposit_type: Deposit type (bike_rc, laptop, cheque, cash)
        base_rental: Base rental amount
        discount: Discount amount
        total: Total amount
        coupon_id: Optional coupon ID
        home_delivery: Whether home delivery is selected
        delivery_address: Delivery address if home delivery
        delivery_latitude: Delivery latitude if home delivery
        delivery_longitude: Delivery longitude if home delivery
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        JSON response with temp_order_id
    """
    try:
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
        
        # Parse datetimes
        try:
            pickup_str = pickup_datetime.replace('Z', '+00:00') if 'Z' in pickup_datetime else pickup_datetime
            end_str = end_datetime.replace('Z', '+00:00') if 'Z' in end_datetime else end_datetime
            
            try:
                pickup_dt = datetime.fromisoformat(pickup_str)
            except ValueError:
                pickup_dt = datetime.strptime(pickup_datetime, '%Y-%m-%dT%H:%M')
            
            try:
                end_dt = datetime.fromisoformat(end_str)
            except ValueError:
                end_dt = datetime.strptime(end_datetime, '%Y-%m-%dT%H:%M')
        except Exception as e:
            logger.error(f"Error parsing datetimes: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid datetime format"
            )
        
        # Validate damage_protection value
        if damage_protection not in [0, 277, 477]:
            damage_protection = 0  # Default to 0 if invalid
        
        # Validate deposit_type
        valid_deposit_types = ['bike_rc', 'laptop', 'cheque', 'cash']
        if deposit_type not in valid_deposit_types:
            deposit_type = 'bike_rc'  # Default to bike_rc if invalid
        
        # Convert home_delivery string to boolean
        home_delivery_bool = home_delivery.lower() in ('true', '1', 'yes', 'on') if home_delivery else False
        
        # Parse delivery coordinates
        delivery_lat = None
        delivery_lng = None
        if delivery_latitude and delivery_longitude:
            try:
                delivery_lat = float(delivery_latitude)
                delivery_lng = float(delivery_longitude)
            except (ValueError, TypeError):
                logger.warning(f"Invalid delivery coordinates: {delivery_latitude}, {delivery_longitude}")
        
        # Calculate advance amount (typically 20-30% of total, or full amount for small bookings)
        # For now, use the total as advance amount
        advance_amount = total
        pay_at_car = 0.0  # Remaining amount to pay at car pickup
        
        # Create temporary order
        temp_order = TempOrders(
            user_id=user_id,
            car_id=car_id,
            start_time=pickup_dt,
            end_time=end_dt,
            advance_amount=advance_amount,
            total_amount=total,
            pay_at_car=pay_at_car
        )
        
        # Store delivery info in sessionStorage via response (we'll pass it through to final order)
        # Since TempOrders doesn't have delivery fields, we'll store in response metadata
        
        db.add(temp_order)
        db.commit()
        db.refresh(temp_order)
        
        logger.info(f"Temporary order created: {temp_order.id} for user {user_id}")
        
        return {
            "success": True,
            "temp_order_id": temp_order.id,
            "message": "Temporary order created successfully",
            "damage_protection": damage_protection,
            "deposit_type": deposit_type,
            "delivery_info": {
                "home_delivery": home_delivery_bool,
                "delivery_address": delivery_address,
                "delivery_latitude": delivery_lat,
                "delivery_longitude": delivery_lng
            } if home_delivery_bool else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating temporary order: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create temporary order"
        )


@router.get("/create")
async def create_payment(
    request: Request,
    order_id: int,
    coupon_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create payment order with CCAvenue
    
    Args:
        request: FastAPI request object
        order_id: Temporary order ID (TempOrders)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        HTML response with payment form
    """
    try:
        if current_user.get("error"):
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
        # Get temporary order from database
        temp_order = db.query(TempOrders).filter(TempOrders.id == order_id).first()
        
        if not temp_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Verify order belongs to current user
        if temp_order.user_id != current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access to order"
            )
        
        # Get user details
        user = db.query(UserProfile).filter(UserProfile.id == temp_order.user_id).first()
        # Validate CCAvenue credentials
        if not settings.CCAVENUE_MERCHANT_ID or not settings.CCAVENUE_ACCESS_CODE or not settings.CCAVENUE_WORKING_KEY:
            logger.error("CCAvenue credentials not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Payment gateway not configured. Please contact support."
            )
        
        # Log credential status (without exposing actual values)
        logger.info(f"CCAvenue credentials check - Merchant ID: {'Set' if settings.CCAVENUE_MERCHANT_ID else 'Missing'}, "
                   f"Access Code: {'Set' if settings.CCAVENUE_ACCESS_CODE else 'Missing'}, "
                   f"Working Key: {'Set' if settings.CCAVENUE_WORKING_KEY else 'Missing'}, "
                   f"Environment: {settings.CCAVENUE_ENVIRONMENT}")
        
        # coupon_id is passed as query parameter
        
        # Get delivery info from query params or request
        delivery_address = request.query_params.get('delivery_address')
        delivery_latitude = request.query_params.get('delivery_latitude')
        delivery_longitude = request.query_params.get('delivery_longitude')
        home_delivery_param = request.query_params.get('home_delivery', 'false')
        home_delivery_bool = home_delivery_param.lower() in ('true', '1', 'yes', 'on')
        
        # Get damage_protection and deposit_type from query params
        damage_protection = request.query_params.get('damage_protection', '0')
        deposit_type = request.query_params.get('deposit_type', 'bike_rc')
        
        # Validate damage_protection
        try:
            damage_protection = int(damage_protection)
            if damage_protection not in [0, 277, 477]:
                damage_protection = 0
        except (ValueError, TypeError):
            damage_protection = 0
        
        # Validate deposit_type
        valid_deposit_types = ['bike_rc', 'laptop', 'cheque', 'cash']
        if deposit_type not in valid_deposit_types:
            deposit_type = 'bike_rc'
        
        # Parse delivery coordinates
        delivery_lat = None
        delivery_lng = None
        if delivery_latitude and delivery_longitude:
            try:
                delivery_lat = float(delivery_latitude)
                delivery_lng = float(delivery_longitude)
            except (ValueError, TypeError):
                logger.warning(f"Invalid delivery coordinates: {delivery_latitude}, {delivery_longitude}")
        
        # Create permanent order from temp order
        new_order = Orders(
            user_id=temp_order.user_id,
            car_id=temp_order.car_id,
            start_time=temp_order.start_time,
            end_time=temp_order.end_time,
            pay_advance_amount=temp_order.advance_amount,
            pay_at_car=temp_order.pay_at_car,
            total_amount=temp_order.total_amount,
            coupon_id=coupon_id,
            advance_amount_status=PaymentStatus.INITIATED,
            home_delivery=home_delivery_bool,
            delivery_address=delivery_address if home_delivery_bool else None,
            delivery_latitude=delivery_lat if home_delivery_bool else None,
            delivery_longitude=delivery_lng if home_delivery_bool else None
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        
        # Generate unique order ID for CCAvenue
        ccavenue_order_id = f"GOGO{new_order.id}{uuid.uuid4().hex[:8].upper()}"
        
        # Convert amount to rupees (if stored in paise)
        amount = temp_order.advance_amount
        if amount > 10000:  # If amount seems too large, might be in paise
            amount = amount / 100
        
        # Create order data
        try:
            order_data = ccavenue_service.create_order_data(
                order_id=ccavenue_order_id,
                amount=amount,
                currency="INR",
                redirect_url=settings.CCAVENUE_REDIRECT_URL,
                cancel_url=settings.CCAVENUE_CANCEL_URL,
                billing_name=f"{user.firstname} {user.lastname}",
                billing_email=user.email,
                billing_tel=user.phone or "",
                billing_address=user.permanentaddress or "",
                merchant_param1=str(new_order.id),  # Store our order ID
                merchant_param2=str(new_order.user_id),  # Store user ID
                merchant_param3=str(damage_protection),  # Store damage protection level
                merchant_param4=deposit_type,  # Store deposit type
            )
            
            logger.info(f"Order data created: order_id={ccavenue_order_id}, amount={amount}")
            
            # Get payment form data
            form_data = ccavenue_service.get_payment_form_data(order_data)
            logger.info(f"Payment form data prepared successfully")
        except ValueError as e:
            logger.error(f"CCAvenue configuration error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment gateway configuration error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error preparing payment data: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to prepare payment data. Please check CCAvenue configuration."
            )
        
        # Update order with CCAvenue order ID
        new_order.order_id = ccavenue_order_id
        new_order.advance_amount_status = PaymentStatus.ORDER_CREATED
        db.commit()
        
        # Delete temporary order
        db.delete(temp_order)
        db.commit()
        
        logger.info(f"Payment order created for order ID: {new_order.id}, CCAvenue order ID: {ccavenue_order_id}")
        
        # Return HTML form that auto-submits to CCAvenue
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Redirecting to Payment Gateway...</title>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        </head>
        <body>
            <form id="paymentForm" method="post" action="{ccavenue_service.payment_url}">
                <input type="hidden" name="encRequest" value="{form_data['encRequest']}"/>
                <input type="hidden" name="access_code" value="{form_data['access_code']}"/>
                <input type="hidden" name="merchant_id" value="{ccavenue_service.merchant_id}"/>
            </form>
            <script>
                document.getElementById('paymentForm').submit();
            </script>
            <p>Redirecting to payment gateway...</p>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment order"
        )


@router.post("/callback")
async def payment_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle payment callback from CCAvenue
    
    Args:
        request: FastAPI request object
        encResponse: Encrypted response from CCAvenue
        db: Database session
        
    Returns:
        Redirect response to success/failure page
    """
    try:
        
        form = await request.form()  # MUST await first
        encResponse = form.get("encResp") or form.get("encResponse")
        if not encResponse:
            logger.error("encResponse not found in request. FORM RECEIVED: %s", form)
            return RedirectResponse(url="/payments/failure?error=invalid_response")
        # Decrypt and verify payment response
        response_data = ccavenue_service.verify_payment(encResponse)
        
        order_id = response_data.get("order_id", "")
        tracking_id = response_data.get("tracking_id", "")
        bank_ref_no = response_data.get("bank_ref_no", "")
        order_status = response_data.get("order_status", "")
        failure_message = response_data.get("failure_message", "")
        payment_mode = response_data.get("payment_mode", "")
        card_name = response_data.get("card_name", "")
        status_code = response_data.get("status_code", "")
        status_message = response_data.get("status_message", "")
        currency = response_data.get("currency", "")
        amount = response_data.get("amount", "")
        
        # Extract our order ID from merchant_param1
        merchant_param1 = response_data.get("merchant_param1", "")
        merchant_param3 = response_data.get("merchant_param3", "0")  # damage_protection
        merchant_param4 = response_data.get("merchant_param4", "bike_rc")  # deposit_type
        
        if not merchant_param1:
            logger.error("Merchant param1 not found in payment response")
            return RedirectResponse(url="/payments/failure?error=invalid_response")
        
        try:
            order_db_id = int(merchant_param1)
            damage_protection = int(merchant_param3) if merchant_param3 else 0
            deposit_type = merchant_param4 if merchant_param4 else "bike_rc"
        except ValueError:
            logger.error(f"Invalid order ID in merchant_param1: {merchant_param1}")
            return RedirectResponse(url="/payments/failure?error=invalid_order")
        
        # Log damage protection and deposit type for reference
        logger.info(f"Order {order_db_id} - Damage Protection: {damage_protection}, Deposit Type: {deposit_type}")
        
        # Get order from database
        order = db.query(Orders).filter(Orders.id == order_db_id).first()
        
        if not order:
            logger.error(f"Order not found: {order_db_id}")
            return RedirectResponse(url="/payments/failure?error=order_not_found")
        
        # Update order based on payment status
        if order_status == "Success":
            order.advance_amount_status = PaymentStatus.SUCCESSFUL
            order.payment_id = tracking_id
            order.payment_mode = payment_mode
            order.order_status = BookingStatus.BOOKED
            order.payment_source = "CCAvenue"
            
            # Apply coupon usage count increment if coupon was used
            if order.coupon_id:
                offer_service.apply_coupon(db, order.coupon_id)
            
            db.commit()
            
            # Refresh to get relationships
            db.refresh(order)
            
            # Send WebSocket notification to admins
            try:
                from app.utils.websocket_manager import websocket_manager
                from sqlalchemy.orm import joinedload
                # Reload order with relationships for notification
                order_with_details = db.query(Orders).options(
                    joinedload(Orders.user),
                    joinedload(Orders.car)
                ).filter(Orders.id == order.id).first()
                
                if order_with_details and order_with_details.user and order_with_details.car:
                    await websocket_manager.send_notification(
                        notification_type="booking",
                        data={
                            "booking_id": order.id,
                            "user_name": f"{order_with_details.user.firstname} {order_with_details.user.lastname}".strip() or order_with_details.user.username,
                            "car_name": f"{order_with_details.car.brand} {order_with_details.car.car_model}",
                            "start_time": order.start_time.isoformat() if order.start_time else None,
                            "total_amount": float(order.total_amount or order.pay_advance_amount or 0)
                        }
                    )
            except Exception as e:
                logger.error(f"Error sending WebSocket notification for booking: {str(e)}")
                # Don't fail the payment if notification fails
            
            # Send confirmation email
            try:
                # Get user details
                user = db.query(UserProfile).filter(UserProfile.id == order.user_id).first()
                if user and user.email:
                    # Get car details
                    from app.db.models import Cars
                    car = db.query(Cars).filter(Cars.id == order.car_id).first()
                    
                    if car:
                        # Format dates
                        start_date_str = order.start_time.strftime("%B %d, %Y at %I:%M %p") if order.start_time else "N/A"
                        end_date_str = order.end_time.strftime("%B %d, %Y at %I:%M %p") if order.end_time else "N/A"
                        
                        user_name = f"{user.firstname} {user.lastname}".strip() or user.username
                        car_name = f"{car.brand} {car.car_model}"
                        
                        email_service.send_booking_confirmation(
                            to_email=user.email,
                            user_name=user_name,
                            booking_id=str(order.id),
                            car_name=car_name,
                            car_brand=car.brand,
                            car_model=car.car_model,
                            registration_number=car.registration_number,
                            start_date=start_date_str,
                            end_date=end_date_str,
                            pickup_location=order.pickup_location,
                            drop_location=order.drop_location,
                            total_amount=float(order.total_amount or order.pay_advance_amount or 0),
                            advance_amount=float(order.pay_advance_amount or 0),
                            payment_mode=payment_mode,
                            tracking_id=tracking_id
                        )
                        logger.info(f"Booking confirmation email sent to {user.email} for order {order.id}")
                    else:
                        logger.warning(f"Car not found for order {order.id}, skipping email")
                else:
                    logger.warning(f"User email not found for order {order.id}, skipping email")
            except Exception as email_error:
                # Don't fail the payment if email fails
                logger.error(f"Error sending booking confirmation email: {str(email_error)}", exc_info=True)
            
            logger.info(f"Payment successful for order ID: {order.id}, Tracking ID: {tracking_id}")
            return RedirectResponse(url="/orders/view")
        else:
            order.advance_amount_status = PaymentStatus.FAILED
            order.payment_id = tracking_id
            order.payment_error_code = status_code
            order.payment_description = failure_message or status_message
            order.error_reason = failure_message
            order.payment_source = "CCAvenue"
            db.commit()
            
            logger.warning(f"Payment failed for order ID: {order.id}, Error: {failure_message}")
            return RedirectResponse(url=f"/payments/failure?order_id={order.id}&error={failure_message}")
            
    except Exception as e:
        logger.error(f"Error processing payment callback: {str(e)}", exc_info=True)
        db.rollback()
        return RedirectResponse(url="/payments/failure?error=processing_error")


@router.get("/success")
async def payment_success(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Payment success page
    
    Args:
        request: FastAPI request object
        order_id: Order ID
        db: Database session
        
    Returns:
        HTML response with success message
    """
    try:
        order = db.query(Orders).filter(Orders.id == order_id).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Render success template
        from app.core.templates import templates
        
        return templates.TemplateResponse(
            "payments/success.html",
            {
                "request": request,
                "order": order
            }
        )
    except Exception as e:
        logger.error(f"Error rendering success page: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to render success page"
        )


@router.get("/failure")
async def payment_failure(
    request: Request,
    order_id: Optional[int] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Payment failure page
    
    Args:
        request: FastAPI request object
        order_id: Optional order ID
        error: Error message
        db: Database session
        
    Returns:
        HTML response with failure message
    """
    try:
        order = None
        if order_id:
            order = db.query(Orders).filter(Orders.id == order_id).first()
        
        # Render failure template
        from app.core.templates import templates
        
        return templates.TemplateResponse(
            "payments/failure.html",
            {
                "request": request,
                "order": order,
                "error": error
            }
        )
    except Exception as e:
        logger.error(f"Error rendering failure page: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to render failure page"
        )


@router.get("/cancel")
async def payment_cancel(
    request: Request,
    order_id: Optional[int] = None
):
    """
    Payment cancellation page
    
    Args:
        request: FastAPI request object
        order_id: Optional order ID
        
    Returns:
        Redirect response to orders page
    """
    logger.info(f"Payment cancelled for order ID: {order_id}")
    return RedirectResponse(url="/orders")

