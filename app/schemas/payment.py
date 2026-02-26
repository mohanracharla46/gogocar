from pydantic import BaseModel

class PaymentInitiateRequest(BaseModel):
    """Schema for mobile payment initiation request"""
    booking_id: int

class PaymentInitiateResponse(BaseModel):
    """Schema for mobile payment initiation response"""
    payment_id: int
    booking_id: int
    amount: float
    status: str

class PaymentVerifyRequest(BaseModel):
    """Schema for mobile payment verification request"""
    payment_id: int
    status: str  # SUCCESS or FAILED


class PaymentVerifyResponse(BaseModel):
    """Schema for mobile payment verification response"""
    message: str
    payment_status: str
    booking_status: str
