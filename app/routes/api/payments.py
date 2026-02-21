from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Orders, PaymentLog, PaymentStatus, UserProfile, BookingStatus
from app.schemas.payment import PaymentInitiateRequest, PaymentInitiateResponse, PaymentVerifyRequest, PaymentVerifyResponse
from app.routes.mobile import get_current_user

router = APIRouter()

@router.post("/initiate", response_model=PaymentInitiateResponse)
async def initiate_mobile_payment(
    request: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Initiate a payment for a mobile booking.
    Validates booking ownership and status.
    Creates a PaymentLog record and returns its details.
    """
    # 1. Booking must exist
    booking = db.query(Orders).filter(Orders.id == request.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # 2. Booking must belong to current_user
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this booking")

    # 3. Booking status must be PENDING
    # If it's already BOOKED (confirmed), return 400
    if booking.order_status in [BookingStatus.BOOKED, BookingStatus.APPROVED]:
         raise HTTPException(status_code=400, detail="Booking is already confirmed/booked")
    
    if booking.order_status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Cannot initiate payment for booking in {booking.order_status} status")

    # 4. Create payment record
    try:
        payment_log = PaymentLog(
            order_id=booking.id,
            user_id=current_user.id,
            amount=booking.total_amount or booking.pay_advance_amount,
            payment_type="ADVANCE",
            payment_status=PaymentStatus.INITIATED,
            payment_gateway="MOBILE_MOCK" # Marking as mobile
        )
        db.add(payment_log)
        db.commit()
        db.refresh(payment_log)

        return {
            "payment_id": payment_log.id,
            "booking_id": booking.id,
            "amount": float(payment_log.amount),
            "status": "INITIATED"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during payment initiation: {str(e)}")

@router.post("/verify", response_model=PaymentVerifyResponse)
async def verify_mobile_payment(
    request: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Verify a mobile payment.
    Updates payment and booking status based on the verification results.
    """
    # 1. Payment must exist
    payment = db.query(PaymentLog).filter(PaymentLog.id == request.payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # 2. Payment must belong to current_user
    if payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this payment")

    # 3. Payment status must be INITIATED
    if payment.payment_status != PaymentStatus.INITIATED:
        raise HTTPException(status_code=400, detail=f"Payment already processed with status: {payment.payment_status}")

    # Get associated booking
    booking = db.query(Orders).filter(Orders.id == payment.order_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Associated booking not found")

    # 4. Process based on status
    try:
        new_payment_status = PaymentStatus.FAILED
        new_booking_status = booking.order_status

        if request.status.upper() == "SUCCESS":
            new_payment_status = PaymentStatus.SUCCESSFUL
            new_booking_status = BookingStatus.BOOKED  # Mapping CONFIRMED to BOOKED
            
            payment.payment_status = new_payment_status
            booking.order_status = new_booking_status
            booking.advance_amount_status = PaymentStatus.SUCCESSFUL
        else:
            new_payment_status = PaymentStatus.FAILED
            # booking.order_status remains PENDING as per requirement
            
            payment.payment_status = new_payment_status
            booking.advance_amount_status = PaymentStatus.FAILED

        db.commit()
        db.refresh(payment)
        db.refresh(booking)

        return {
            "message": "Payment processed",
            "payment_status": str(new_payment_status.value),
            "booking_status": str(new_booking_status.value)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during payment verification: {str(e)}")
