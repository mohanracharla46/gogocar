"""
Database models for GoGoCar application
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, JSON, Float, DateTime,
    ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


def generate_uuid() -> str:
    """Generate a unique UUID string"""
    return str(uuid.uuid4())


# Enums
class FuelType(str, PyEnum):
    """Fuel type enumeration"""
    PETROL = "PETROL"
    DIESEL = "DIESEL"
    CNG = "CNG"


class TransmissionType(str, PyEnum):
    """Transmission type enumeration"""
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"


class NoOfSeats(str, PyEnum):
    """Number of seats enumeration"""
    FIVE = "FIVE"
    SEVEN = "SEVEN"


class CarType(str, PyEnum):
    """Car type enumeration"""
    SUV = "SUV"
    SEDAN = "SEDAN"
    HATCHBACK = "HATCHBACK"


class PaymentStatus(str, PyEnum):
    """Payment status enumeration"""
    INITIATED = "INITIATED"
    ORDER_CREATED = "ORDER_CREATED"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    REFUND_INITIATED = "REFUND_INITIATED"


class BookingStatus(str, PyEnum):
    """Booking status enumeration"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    BOOKED = "BOOKED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class KYCStatus(str, PyEnum):
    """KYC verification status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NOT_SUBMITTED = "NOT_SUBMITTED"


class TicketStatus(str, PyEnum):
    """Support ticket status"""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class MaintenanceType(str, PyEnum):
    """Maintenance type"""
    ROUTINE = "ROUTINE"
    REPAIR = "REPAIR"
    DAMAGE = "DAMAGE"
    SERVICE = "SERVICE"


# Models
class UserProfile(Base):
    """User profile model"""
    __tablename__ = 'user_profiles'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)  # Added for manual auth
    isadmin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # Enable/disable user
    aadhaar_front = Column(String, nullable=True)
    aadhaar_back = Column(String, nullable=True)
    drivinglicense_front = Column(String, nullable=True)
    drivinglicense_back = Column(String, nullable=True)
    permanentaddress = Column(String, nullable=True)
    phone = Column(String(12), nullable=True)
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.NOT_SUBMITTED, nullable=False)
    kyc_approved_by = Column(Integer, ForeignKey('user_profiles.id'), nullable=True)
    kyc_approved_at = Column(DateTime, nullable=True)
    kyc_rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relationships
    approved_by_user = relationship("UserProfile", remote_side=[id])


class Location(Base):
    """Location model for car pickup/drop locations"""
    __tablename__ = 'locations'
    
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, nullable=False, unique=True)
    maps_link = Column(String, nullable=True)  # Google Maps or other map service link


class Cars(Base):
    """Car model"""
    __tablename__ = 'cars'
    
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, nullable=False)
    car_model = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    base_price = Column(Float, nullable=False)  # Base hourly price
    damage_price = Column(Float, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    protection_price = Column(Float, nullable=False)
    images = Column(String, nullable=True)  # Comma-separated image URLs
    no_of_km = Column(Integer, nullable=False)
    fuel_type = Column(Enum(FuelType), nullable=False)
    transmission_type = Column(Enum(TransmissionType), nullable=False)
    no_of_seats = Column(Enum(NoOfSeats), nullable=False)
    car_type = Column(Enum(CarType), nullable=False)
    maps_link = Column(String, nullable=True)
    prices = Column(JSON, nullable=True)  # {hourly: x, daily: y, weekly: z, extra_km: w, deposit: v}
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)
    # Extended fields for admin
    features = Column(JSON, nullable=True)  # List of features
    tags = Column(JSON, nullable=True)  # List of tags/categories
    registration_number = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    color = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relationships
    location = relationship("Location", backref="cars")
    temp_orders = relationship(
        'TempOrders',
        back_populates='car',
        cascade='all, delete-orphan'
    )
    orders = relationship("Orders", back_populates="car")
    ratings = relationship("Ratings", back_populates="car")
    reviews = relationship("Reviews", back_populates="car")
    availability_blocks = relationship("CarAvailability", back_populates="car", cascade='all, delete-orphan')
    maintenance_logs = relationship("MaintenanceLog", back_populates="car", cascade='all, delete-orphan')
    damage_reports = relationship("DamageReport", back_populates="car", cascade='all, delete-orphan')


class TempOrders(Base):
    """Temporary orders model (pending payment)"""
    __tablename__ = 'temp_orders'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    car_id = Column(Integer, ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    advance_amount = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    pay_at_car = Column(Float, nullable=False)
    
    # Relationships
    car = relationship('Cars', back_populates='temp_orders')
    user = relationship("UserProfile")


class AnonymousUsers(Base):
    """Anonymous users model (for users without login)"""
    __tablename__ = 'anonymous_users'
    
    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    location = Column(String, nullable=False)
    car_id = Column(Integer, nullable=True)
    unique_string = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
        default=generate_uuid
    )


class Coupons(Base):
    """Coupons/Offers model for discounts"""
    __tablename__ = 'coupons'
    
    id = Column(Integer, primary_key=True, index=True)
    coupon_code = Column(String, unique=True, nullable=False, index=True)
    discount = Column(Integer, nullable=False)  # Discount percentage or fixed amount
    discount_type = Column(String, default='PERCENTAGE', nullable=False)  # PERCENTAGE or FIXED
    is_active = Column(Boolean, default=True, nullable=False)
    expiration_time = Column(DateTime, nullable=False)
    usage_limit = Column(Integer, nullable=True)  # Max number of times coupon can be used
    usage_count = Column(Integer, default=0, nullable=False)  # Current usage count
    min_amount = Column(Float, nullable=True)  # Minimum order amount
    max_discount = Column(Float, nullable=True)  # Maximum discount amount
    applicable_to_car_type = Column(JSON, nullable=True)  # List of car types
    applicable_to_car_ids = Column(JSON, nullable=True)  # List of specific car IDs
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)


class Orders(Base):
    """Orders/Bookings model"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    car_id = Column(Integer, ForeignKey('cars.id'), nullable=False)
    coupon_id = Column(Integer, ForeignKey('coupons.id'), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    actual_start_time = Column(DateTime, nullable=True)  # Actual pickup time
    actual_end_time = Column(DateTime, nullable=True)  # Actual return time
    pay_advance_amount = Column(Float, nullable=False)
    advance_amount_status = Column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.INITIATED
    )
    pay_at_car = Column(Float, nullable=True)
    pay_at_car_status = Column(Enum(PaymentStatus), nullable=True)
    payment_id = Column(String, nullable=True)
    order_id = Column(String, nullable=True, index=True)
    payment_mode = Column(String, nullable=True)
    payment_proofs = Column(String, nullable=True)
    order_status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.PENDING)
    no_of_km_travelled = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    extra_hours_charge = Column(Float, nullable=True)  # Late return charges
    extra_km_charge = Column(Float, nullable=True)  # Extra km charges
    deposit_amount = Column(Float, nullable=True)
    deposit_returned = Column(Boolean, default=False, nullable=False)
    refund_amount = Column(Float, nullable=True)
    refund_status = Column(Enum(PaymentStatus), nullable=True)
    payment_error_code = Column(String, nullable=True)
    payment_description = Column(String, nullable=True)
    payment_source = Column(String, nullable=True)
    payment_step = Column(String, nullable=True)
    error_reason = Column(String, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by = Column(Integer, ForeignKey('user_profiles.id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    assigned_by = Column(Integer, ForeignKey('user_profiles.id'), nullable=True)  # Admin who assigned
    signature = Column(String, nullable=True)
    pickup_location = Column(String, nullable=True)
    drop_location = Column(String, nullable=True)
    home_delivery = Column(Boolean, default=False, nullable=False)
    delivery_address = Column(Text, nullable=True)
    delivery_latitude = Column(Float, nullable=True)  # GPS latitude for home delivery
    delivery_longitude = Column(Float, nullable=True)  # GPS longitude for home delivery
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relationships
    user = relationship("UserProfile", backref="orders", foreign_keys=[user_id])
    car = relationship("Cars", back_populates="orders")
    coupon = relationship("Coupons")
    cancelled_by_user = relationship("UserProfile", foreign_keys=[cancelled_by])
    assigned_by_user = relationship("UserProfile", foreign_keys=[assigned_by])
    payment_logs = relationship("PaymentLog", back_populates="order", cascade='all, delete-orphan')


class Ratings(Base):
    """Ratings model for car ratings"""
    __tablename__ = 'ratings'
    
    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey('cars.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    
    # Relationships
    car = relationship("Cars", back_populates="ratings")
    user = relationship("UserProfile")


class Reviews(Base):
    """Reviews model for car reviews with text"""
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey('cars.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5
    review_text = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)  # Admin approval
    is_hidden = Column(Boolean, default=False, nullable=False)  # Admin can hide
    approved_by = Column(Integer, ForeignKey('user_profiles.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relationships
    car = relationship("Cars", back_populates="reviews")
    user = relationship("UserProfile", foreign_keys=[user_id])
    order = relationship("Orders")
    approved_by_user = relationship("UserProfile", foreign_keys=[approved_by])


class Contact(Base):
    """Contact form model"""
    __tablename__ = 'contacts'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


# New models for admin features

class CarAvailability(Base):
    """Car availability blocking model (for maintenance, damage, etc.)"""
    __tablename__ = 'car_availability'
    
    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(String, nullable=True)  # maintenance, damage, booked, etc.
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('user_profiles.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    
    # Relationships
    car = relationship("Cars", back_populates="availability_blocks")
    created_by_user = relationship("UserProfile")


class PaymentLog(Base):
    """Payment transaction logs"""
    __tablename__ = 'payment_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    amount = Column(Float, nullable=False)
    payment_type = Column(String, nullable=False)  # ADVANCE, BALANCE, DEPOSIT, REFUND, EXTRA_CHARGES
    payment_status = Column(Enum(PaymentStatus), nullable=False)
    payment_gateway = Column(String, default='CCAVENUE', nullable=False)
    gateway_transaction_id = Column(String, nullable=True)
    gateway_order_id = Column(String, nullable=True)
    gateway_response = Column(JSON, nullable=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    
    # Relationships
    order = relationship("Orders", back_populates="payment_logs")
    user = relationship("UserProfile")


class MaintenanceLog(Base):
    """Car maintenance tracking"""
    __tablename__ = 'maintenance_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)
    maintenance_type = Column(Enum(MaintenanceType), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    cost = Column(Float, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # NULL if ongoing
    service_provider = Column(String, nullable=True)
    photos = Column(String, nullable=True)  # Comma-separated image URLs
    created_by = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relationships
    car = relationship("Cars", back_populates="maintenance_logs")
    created_by_user = relationship("UserProfile")


class DamageReport(Base):
    """Car damage reports"""
    __tablename__ = 'damage_reports'
    
    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    reported_by = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    damage_description = Column(Text, nullable=False)
    damage_photos = Column(String, nullable=True)  # Comma-separated image URLs
    repair_cost = Column(Float, nullable=True)
    repair_status = Column(String, default='PENDING', nullable=False)  # PENDING, IN_REPAIR, REPAIRED
    repaired_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relationships
    car = relationship("Cars", back_populates="damage_reports")
    order = relationship("Orders")
    reported_by_user = relationship("UserProfile")


class SupportTicket(Base):
    """Support ticket system"""
    __tablename__ = 'support_tickets'
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=True)  # NULL for guest tickets
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(String, default='MEDIUM', nullable=False)  # LOW, MEDIUM, HIGH, URGENT
    assigned_to = Column(Integer, ForeignKey('user_profiles.id'), nullable=True)  # Admin user
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey('user_profiles.id'), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relationships
    user = relationship("UserProfile", foreign_keys=[user_id])
    order = relationship("Orders")
    assigned_to_user = relationship("UserProfile", foreign_keys=[assigned_to])
    resolved_by_user = relationship("UserProfile", foreign_keys=[resolved_by])
    messages = relationship("TicketMessage", back_populates="ticket", order_by="TicketMessage.created_at.asc()")


class TicketMessage(Base):
    """Ticket conversation messages"""
    __tablename__ = 'ticket_messages'
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.id'), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=True)  # NULL for customer, admin user_id for admin
    is_admin = Column(Boolean, default=False, nullable=False)  # True if sent by admin
    message = Column(Text, nullable=False)
    attachment_url = Column(String, nullable=True)  # S3 URL for attached images
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    
    # Relationships
    ticket = relationship("SupportTicket", back_populates="messages")
    sender = relationship("UserProfile", foreign_keys=[sender_id])


class Notification(Base):
    """User notifications"""
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)  # BOOKING, PAYMENT, KYC, SYSTEM, etc.
    related_order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    
    # Relationships
    user = relationship("UserProfile")
    related_order = relationship("Orders")

