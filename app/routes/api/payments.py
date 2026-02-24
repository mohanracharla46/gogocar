"""
Mobile payment endpoints
  POST /api/payments/initiate – initiate a payment for a pending booking
  POST /api/payments/verify   – verify payment status and update booking to BOOKED
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Orders, PaymentLog, PaymentStatus, UserProfile, BookingStatus
from app.routes.mobile import get_current_user
from app.schemas.mobile import (
    MobilePaymentInitiateRequest,
    MobilePaymentInitiateResponse,
    MobilePaymentVerifyRequest,
    MobilePaymentVerifyResponse
)

router = APIRouter()

@router.post("/initiate", response_model=MobilePaymentInitiateResponse)
async def initiate_mobile_payment(
    request: MobilePaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Initiate a payment for a mobile booking.
    Enforces that booking is PENDING and no successful payment exists.
    """
    # 1. Booking validation
    booking = db.query(Orders).filter(Orders.id == request.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this booking")

    if booking.order_status != BookingStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Booking is in {booking.order_status.value} status. Only PENDING bookings can initiate payment."
        )

    # 2. Check for existing successful payments
    success_payment = db.query(PaymentLog).filter(
        PaymentLog.order_id == booking.id,
        PaymentLog.payment_status == PaymentStatus.SUCCESSFUL
    ).first()
    
    if success_payment:
        raise HTTPException(status_code=400, detail="Booking already has a successful payment.")

    # 3. Create payment record
    try:
        payment_log = PaymentLog(
            order_id=booking.id,
            user_id=current_user.id,
            amount=booking.total_amount or booking.pay_advance_amount,
            payment_type="ADVANCE",
            payment_status=PaymentStatus.INITIATED,
            payment_gateway="MOBILE_MOCK"
        )
        db.add(payment_log)
        db.commit()
        db.refresh(payment_log)

        return {
            "booking_id": booking.id,
            "payment_id": payment_log.id,
            "amount": float(payment_log.amount)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/verify", response_model=MobilePaymentVerifyResponse)
async def verify_mobile_payment(
    request: MobilePaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Verify a mobile payment with strict state transitions and idempotency.
    Uses row-level locking on the booking to prevent race conditions.
    """
    try:
        # 1. Payment validation
        payment = db.query(PaymentLog).filter(PaymentLog.id == request.payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment record not found")

        if payment.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized for this payment")

        # 2. IDEMPOTENCY: If already successful, return success response
        if payment.payment_status == PaymentStatus.SUCCESSFUL:
            # Check associated booking status to be sure
            booking_check = db.query(Orders).filter(Orders.id == payment.order_id).first()
            return {
                "success": True,
                "booking_status": str(booking_check.order_status.value) if booking_check else "BOOKED"
            }

        # 3. Lock booking row and validate
        booking = (
            db.query(Orders)
            .filter(Orders.id == payment.order_id)
            .with_for_update()
            .first()
        )
        
        if not booking:
            raise HTTPException(status_code=404, detail="Associated booking not found")

        if booking.order_status != BookingStatus.PENDING:
            # If booking is already BOOKED but payment was INITIATED, we might have a race
            if booking.order_status == BookingStatus.BOOKED:
                 # Check if some other payment succeeded
                 return {"success": True, "booking_status": "BOOKED"}
            raise HTTPException(status_code=400, detail=f"Booking is in {booking.order_status.value} status.")

        # 4. Amount validation
        expected_amount = booking.total_amount or booking.pay_advance_amount
        if abs(float(payment.amount) - float(expected_amount)) > 0.01:
            raise HTTPException(status_code=400, detail="Payment amount does not match booking amount.")

        # 5. Process state transition
        if request.status.upper() == "SUCCESS":
            payment.payment_status = PaymentStatus.SUCCESSFUL
            payment.gateway_transaction_id = request.transaction_id
            
            booking.order_status = BookingStatus.BOOKED
            booking.advance_amount_status = PaymentStatus.SUCCESSFUL
            success = True
        else:
            payment.payment_status = PaymentStatus.FAILED
            payment.gateway_transaction_id = request.transaction_id
            booking.advance_amount_status = PaymentStatus.FAILED
            success = False

        db.commit()
        return {
            "success": success,
            "booking_status": str(booking.order_status.value)
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
