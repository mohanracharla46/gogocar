"""
Admin page routes (HTML templates)
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.db.session import get_db
from app.routes.auth import get_current_user
from app.routes.admin.dependencies import require_admin
from app.core.logging_config import logger

router = APIRouter(
    prefix="/admin",
    tags=["admin-pages"]
)


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin dashboard page"""
    from app.services.analytics_service import analytics_service
    from app.core.config import settings
    from app.db.models import Orders, BookingStatus
    from datetime import datetime, timedelta
    
    try:
        stats = analytics_service.get_dashboard_stats(db)
        
        # Quick action counts
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        new_bookings = db.query(Orders).filter(
            Orders.order_status == BookingStatus.PENDING
        ).count()
        
        todays_deliveries = db.query(Orders).filter(
            Orders.start_time >= today_start,
            Orders.start_time < today_end,
            Orders.order_status.in_([BookingStatus.BOOKED, BookingStatus.APPROVED])
        ).count()
        
        todays_pickups = db.query(Orders).filter(
            Orders.end_time >= today_start,
            Orders.end_time < today_end,
            Orders.order_status == BookingStatus.ONGOING
        ).count()
        
        ongoing_bookings = db.query(Orders).filter(
            Orders.order_status == BookingStatus.ONGOING
        ).count()
        
        return templates.TemplateResponse(
            "admin/dashboard.html",
            {
                "request": request,
                "stats": stats,
                "user_info": current_user,
                "is_authenticated": True,
                "new_bookings": new_bookings,
                "todays_deliveries": todays_deliveries,
                "todays_pickups": todays_pickups,
                "ongoing_bookings": ongoing_bookings,
            }
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return templates.TemplateResponse(
            "admin/dashboard.html",
            {
                "request": request,
                "stats": None,
                "user_info": current_user,
                "is_authenticated": True,
                "error": str(e),
                "new_bookings": 0,
                "todays_deliveries": 0,
                "todays_pickups": 0,
                "ongoing_bookings": 0,
            }
        )


@router.get("/cars", response_class=HTMLResponse)
async def admin_cars(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin cars page"""
    return templates.TemplateResponse(
        "admin/cars.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True
        }
    )


@router.get("/cars/create", response_class=HTMLResponse)
async def admin_cars_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin create car page"""
    from app.db.models import Location, CarType, FuelType, TransmissionType, NoOfSeats
    
    locations = db.query(Location).all()
    
    return templates.TemplateResponse(
        "admin/car_form.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True,
            "car": None,
            "locations": locations,
            "car_types": [t.value for t in CarType],
            "fuel_types": [t.value for t in FuelType],
            "transmission_types": [t.value for t in TransmissionType],
            "seat_options": [s.value for s in NoOfSeats]
        }
    )


@router.get("/cars/{car_id}/edit", response_class=HTMLResponse)
async def admin_cars_edit(
    request: Request,
    car_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin edit car page"""
    from app.db.models import Cars, Location, CarType, FuelType, TransmissionType, NoOfSeats
    
    car = db.query(Cars).filter(Cars.id == car_id).first()
    if not car:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/admin/cars", status_code=302)
    
    locations = db.query(Location).all()
    
    return templates.TemplateResponse(
        "admin/car_form.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True,
            "car": car,
            "locations": locations,
            "car_types": [t.value for t in CarType],
            "fuel_types": [t.value for t in FuelType],
            "transmission_types": [t.value for t in TransmissionType],
            "seat_options": [s.value for s in NoOfSeats]
        }
    )


@router.get("/bookings", response_class=HTMLResponse)
async def admin_bookings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin bookings page"""
    from app.db.models import Orders, BookingStatus
    from datetime import datetime, timedelta
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    new_bookings = db.query(Orders).filter(
        Orders.order_status == BookingStatus.PENDING
    ).count()
    
    todays_deliveries = db.query(Orders).filter(
        Orders.start_time >= today_start,
        Orders.start_time < today_end,
        Orders.order_status.in_([BookingStatus.BOOKED, BookingStatus.APPROVED])
    ).count()
    
    todays_pickups = db.query(Orders).filter(
        Orders.end_time >= today_start,
        Orders.end_time < today_end,
        Orders.order_status == BookingStatus.ONGOING
    ).count()
    
    ongoing_bookings = db.query(Orders).filter(
        Orders.order_status == BookingStatus.ONGOING
    ).count()
    
    return templates.TemplateResponse(
        "admin/bookings.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True,
            "new_bookings": new_bookings,
            "todays_deliveries": todays_deliveries,
            "todays_pickups": todays_pickups,
            "ongoing_bookings": ongoing_bookings,
        }
    )


@router.get("/bookings/{booking_id}", response_class=HTMLResponse)
async def admin_booking_detail(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin booking detail page"""
    from app.db.models import Orders
    from sqlalchemy.orm import joinedload
    
    # Eagerly load car and user relationships
    booking = db.query(Orders).options(
        joinedload(Orders.car),
        joinedload(Orders.user)
    ).filter(Orders.id == booking_id).first()
    
    if not booking:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/admin/bookings", status_code=302)
    
    return templates.TemplateResponse(
        "admin/booking_detail.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True,
            "booking": booking
        }
    )


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin users page"""
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True
        }
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin user detail page"""
    from app.db.models import UserProfile
    
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/admin/users", status_code=302)
    
    return templates.TemplateResponse(
        "admin/user_detail.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True,
            "user": user
        }
    )


@router.get("/offers", response_class=HTMLResponse)
async def admin_offers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin offers page"""
    return templates.TemplateResponse(
        "admin/offers.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True
        }
    )


@router.get("/reviews", response_class=HTMLResponse)
async def admin_reviews(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin reviews page"""
    return templates.TemplateResponse(
        "admin/reviews.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True
        }
    )


@router.get("/maintenance", response_class=HTMLResponse)
async def admin_maintenance(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin maintenance page"""
    return templates.TemplateResponse(
        "admin/maintenance.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True
        }
    )


@router.get("/tickets", response_class=HTMLResponse)
async def admin_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin tickets page"""
    return templates.TemplateResponse(
        "admin/tickets.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True
        }
    )


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
async def admin_ticket_detail(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin ticket detail page"""
    from app.db.models import SupportTicket
    from sqlalchemy.orm import joinedload
    
    from app.db.models import TicketMessage
    
    ticket = db.query(SupportTicket).options(
        joinedload(SupportTicket.user),
        joinedload(SupportTicket.order),
        joinedload(SupportTicket.messages).joinedload(TicketMessage.sender)
    ).filter(SupportTicket.id == ticket_id).first()
    
    if not ticket:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/admin/tickets", status_code=302)
    
    return templates.TemplateResponse(
        "admin/ticket_detail.html",
        {
            "request": request,
            "ticket": ticket,
            "user_info": current_user,
            "is_authenticated": True
        }
    )


@router.get("/analytics", response_class=HTMLResponse)
async def admin_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin analytics page"""
    return templates.TemplateResponse(
        "admin/analytics.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True
        }
    )


@router.get("/locations", response_class=HTMLResponse)
async def admin_locations(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Admin locations page"""
    return templates.TemplateResponse(
        "admin/locations.html",
        {
            "request": request,
            "user_info": current_user,
            "is_authenticated": True
        }
    )

