"""
Main FastAPI application entry point - Final Reload Triggered
"""
from typing import Optional
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

from app.core.config import settings
from app.core.logging_config import logger, setup_logging
from app.core.templates import templates
from app.core.middleware import AuthMiddleware
from app.db.session import init_db, get_db
from app.routes import auth, payments, bookings
from fastapi import Depends
from sqlalchemy.orm import Session
# Include other routes as they are created
# from app.routes import pages, ratings

# Setup logging (logs directory in project root)
# The logging is already configured in app.core.logging_config on import.
# We just need to make sure the logger is available here.
logger.info(f"Starting {settings.APP_NAME} in {'DEBUG' if settings.DEBUG else 'PRODUCTION'} mode")

# Initialize FastAPI app
app = FastAPI(
    # docs_url=None,
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="GoGoCar - Self Drive Car Rental Application",
    debug=settings.DEBUG
)

# CORS middleware
origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    settings.DOMAIN_URL,
]
# Add Render domains if possible
if "onrender.com" in settings.DOMAIN_URL:
    render_domain = settings.DOMAIN_URL
    origins.append(render_domain)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication middleware (add after CORS)
app.add_middleware(AuthMiddleware)

# Mount static files (relative to project root)
from pathlib import Path
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize database
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP exception: {exc.status_code} - {exc.detail}")
    
    # Check if this is an admin page request (not an API request or login page itself)
    path = request.url.path
    is_admin_path = path.startswith("/admin")
    is_admin_api = path.startswith("/admin/api")
    is_admin_auth = path.startswith("/admin/auth")
    
    # If unauthorized/forbidden access to an admin page, redirect to login
    if is_admin_path and not is_admin_api and not is_admin_auth:
        if exc.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]:
            from fastapi.responses import RedirectResponse
            error_type = "unauthorized" if exc.status_code == status.HTTP_401_UNAUTHORIZED else "forbidden"
            return RedirectResponse(
                url=f"/admin/auth/login?error={error_type}&return_url={path}",
                status_code=status.HTTP_302_FOUND
            )

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "details": exc.errors()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "message": str(exc)}
    )


# Include routers
app.include_router(auth.router)
app.include_router(payments.router)
app.include_router(bookings.router)
from app.routes import mobile
app.include_router(mobile.router, prefix="/api/mobile")
from app.routes.api import cars as api_cars
app.include_router(api_cars.router, prefix="/api/cars", tags=["Mobile Cars"])
from app.routes.api import bookings as api_bookings
app.include_router(api_bookings.router, prefix="/api/bookings", tags=["Mobile Bookings"])
from app.routes.api import payments as api_payments
app.include_router(api_payments.router, prefix="/api/payments", tags=["Mobile Payments"])
from app.routes import reviews, tickets
app.include_router(reviews.router)
app.include_router(tickets.router)

# Include admin routers
# IMPORTANT: Include page routes BEFORE API routes to avoid path conflicts
from app.routes.admin import pages as admin_pages
from app.routes.admin import cars as admin_cars, dashboard as admin_dashboard, bookings as admin_bookings
from app.routes.admin import locations as admin_locations, users as admin_users, reviews as admin_reviews, maintenance as admin_maintenance, tickets as admin_tickets, offers as admin_offers, websocket as admin_websocket, auth as admin_auth
from app.routes import offers as customer_offers
app.include_router(admin_auth.router)  # Auth first (login page)
app.include_router(admin_pages.router)  # Pages first
app.include_router(admin_dashboard.router)
app.include_router(admin_cars.router)
app.include_router(admin_bookings.router)
app.include_router(admin_locations.router)
app.include_router(admin_users.router)
app.include_router(admin_reviews.router)
app.include_router(admin_maintenance.router)
app.include_router(admin_tickets.router)
app.include_router(admin_offers.router)
app.include_router(admin_websocket.router)  # WebSocket for notifications
app.include_router(customer_offers.router)


@app.get("/admin")
async def admin_redirect():
    """Redirect /admin to dashboard"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@app.get("/")
async def root(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Root endpoint - render index.html"""
    from app.db.models import Cars, Location
    from sqlalchemy import case
    logger.info("Root endpoint accessed")
    
    try:
        # Get cars ordered by type
        car_order = case(
            (Cars.car_type == 'HATCHBACK', 1),
            (Cars.car_type == 'SEDAN', 2),
            (Cars.car_type == 'SUV', 3),
            else_=5
        )
        cars = db.query(Cars).filter(Cars.active == True).order_by(car_order, Cars.id.desc()).all()
        locations = db.query(Location).all()
        login_url = settings.LOGIN_URL
        
        locations = db.query(Location).all()
        login_url = settings.LOGIN_URL
        
        # Check authentication using current_user dependency
        is_authenticated = not current_user.get("error")
        is_admin = current_user.get("isadmin", False)
        
        # Get featured cars based on bookings
        from app.db.models import Orders
        from app.services.analytics_service import analytics_service
        from sqlalchemy import func
        
        # Check if there are any bookings
        total_bookings = db.query(func.count(Orders.id)).scalar() or 0
        
        featured_cars = []
        if total_bookings > 0:
            # Get top performing cars by category performance
            category_performance = analytics_service.get_category_performance(db)
            top_cars = analytics_service.get_top_performing_cars(db, limit=4)
            featured_cars = top_cars[:4]
        else:
            # No bookings - show any 3-4 active cars from admin panel
            # Get latest added cars (ordered by id descending)
            latest_cars = db.query(Cars).filter(Cars.active == True).order_by(Cars.id.desc()).all()
            # Prefer showing 4 cars if available, otherwise 3
            if len(latest_cars) >= 4:
                featured_cars = latest_cars[:4]
            elif len(latest_cars) >= 3:
                featured_cars = latest_cars[:3]
            else:
                # Show all available cars if less than 3
                featured_cars = latest_cars
        
        # Get latest reviews (5-10)
        from app.db.models import Reviews
        from sqlalchemy.orm import joinedload
        
        reviews = db.query(Reviews).options(
            joinedload(Reviews.user),
            joinedload(Reviews.car)
        ).filter(
            Reviews.is_approved == True,
            Reviews.is_hidden == False
        ).order_by(Reviews.created_at.desc()).limit(10).all()
        
        # Convert cars to dict format for frontend
        featured_cars_data = []
        if total_bookings > 0:
            # featured_cars contains CarPerformance objects, need to fetch full car details
            for car_perf in featured_cars:
                car = db.query(Cars).filter(Cars.id == car_perf.car_id).first()
                if car:
                    featured_cars_data.append({
                        "id": car.id,
                        "brand": car.brand,
                        "car_model": car.car_model,
                        "base_price": float(car.base_price),
                        "images": car.images
                    })
        else:
            # featured_cars contains Cars objects directly
            for car in featured_cars:
                featured_cars_data.append({
                    "id": car.id,
                    "brand": car.brand,
                    "car_model": car.car_model,
                    "base_price": float(car.base_price),
                    "images": car.images
                })
        
        # Convert reviews to dict format
        reviews_data = []
        for review in reviews:
            review_dict = {
                "id": review.id,
                "rating": review.rating,
                "comment": review.review_text or "",  # Use review_text instead of comment
                "user_firstname": review.user.firstname if review.user else "Anonymous",
                "user_lastname": review.user.lastname if review.user else "",
                "car_brand": review.car.brand if review.car else "",
                "car_model": review.car.car_model if review.car else "",
                "created_at": review.created_at.isoformat() if review.created_at else None
            }
            reviews_data.append(review_dict)
        
        logger.debug(f"Rendering index.html with {len(cars)} cars, {len(featured_cars_data)} featured cars, {len(reviews_data)} reviews")
        
        # Convert locations to a format that matches the template
        # The Location model has a 'location' field, not 'name'
        locations_data = [{"name": loc.location, "location": loc.location} for loc in locations]
        
        # Get active offers/coupons
        from app.db.models import Coupons
        from datetime import datetime
        active_offers = db.query(Coupons).filter(
            Coupons.is_active == True,
            Coupons.expiration_time > datetime.now()
        ).order_by(Coupons.created_at.desc()).limit(10).all()
        
        # Convert offers to dict format
        offers_data = []
        for offer in active_offers:
            # Check if offer has reached usage limit
            if offer.usage_limit and offer.usage_count >= offer.usage_limit:
                continue
            
            discount_display = ""
            if offer.discount_type == "PERCENTAGE":
                discount_display = f"{offer.discount}% OFF"
            else:
                discount_display = f"₹{offer.discount} OFF"
            
            offers_data.append({
                "id": offer.id,
                "coupon_code": offer.coupon_code,
                "discount": offer.discount,
                "discount_type": offer.discount_type,
                "discount_display": discount_display,
                "description": offer.description or "",
                "min_amount": float(offer.min_amount) if offer.min_amount else None,
                "expiration_time": offer.expiration_time.isoformat() if offer.expiration_time else None,
                "max_discount": float(offer.max_discount) if offer.max_discount else None
            })
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "login_url": login_url,
                "cars": cars,
                "locations": locations_data,
                "is_authenticated": is_authenticated,
                "is_admin": is_admin,
                "featured_cars": featured_cars_data,
                "reviews": reviews_data,
                "offers": offers_data
            }
        )
    
    except Exception as e:
        logger.error(f"Error rendering index.html: {str(e)}", exc_info=True)
        # Fallback to basic response if template rendering fails
        access_token = request.cookies.get('access_token')
        is_authenticated = access_token is not None and access_token != ''
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "login_url": settings.LOGIN_URL,
                "cars": [],
                "locations": [],
                "is_authenticated": is_authenticated
            }
        )


@app.get("/cars")
async def cars_page(
    request: Request, 
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 12,
    pickup_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
    location: Optional[str] = None,
    current_user: dict = Depends(auth.get_current_user)
):
    """Cars listing page - render cars.html with pagination and date filtering"""
    from app.db.models import Cars, Location, Orders, BookingStatus
    from sqlalchemy import case, and_, or_
    from datetime import datetime
    from app.utils.pagination import paginate_query
    
    logger.info("Cars page accessed")
    
    try:
        # Get cars ordered by type
        car_order = case(
            (Cars.car_type == 'HATCHBACK', 1),
            (Cars.car_type == 'SEDAN', 2),
            (Cars.car_type == 'SUV', 3),
            else_=5
        )
        
        # Base query for active cars - order by category then latest first
        query = db.query(Cars).filter(Cars.active == True).order_by(car_order, Cars.id.desc())
        
        # Filter by location if provided
        if location:
            # Join with Location table and filter by location name
            query = query.join(Location, Cars.location_id == Location.id).filter(Location.location == location)
        
        # Filter by date availability if dates are provided
        if pickup_datetime and end_datetime:
            try:
                # Handle datetime-local format (YYYY-MM-DDTHH:mm) or ISO format
                if 'T' in pickup_datetime:
                    pickup_dt = datetime.fromisoformat(pickup_datetime.replace('Z', '+00:00'))
                else:
                    pickup_dt = datetime.strptime(pickup_datetime, '%Y-%m-%d %H:%M:%S')
                
                if 'T' in end_datetime:
                    end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                else:
                    end_dt = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S')
                
                # Get cars that have conflicting bookings
                # A conflict exists if: booking_start < requested_end AND booking_end > requested_start
                conflicting_car_ids = db.query(Orders.car_id).filter(
                    and_(
                        Orders.order_status.in_([
                            BookingStatus.PENDING,
                            BookingStatus.APPROVED,
                            BookingStatus.BOOKED,
                            BookingStatus.ONGOING
                        ]),
                        Orders.start_time < end_dt,
                        Orders.end_time > pickup_dt
                    )
                ).distinct().all()
                
                # Extract car IDs from tuples
                conflicting_ids = [car_id[0] for car_id in conflicting_car_ids]
                
                # Exclude cars with conflicting bookings
                if conflicting_ids:
                    query = query.filter(~Cars.id.in_(conflicting_ids))
            except Exception as e:
                logger.warning(f"Error parsing dates for filtering: {str(e)}")
        
        # Validate and limit page_size
        page_size = min(max(1, page_size), 100)  # Between 1 and 100
        
        # Paginate
        cars, pagination = paginate_query(query, page=page, page_size=page_size)
        
        locations = db.query(Location).all()
        login_url = settings.LOGIN_URL
        
        # Get unique brands for filter
        unique_brands = db.query(Cars.brand).filter(Cars.active == True).distinct().all()
        brands = [brand[0] for brand in unique_brands]
        
        # Calculate average ratings for each car
        from app.db.models import Reviews
        from sqlalchemy import func
        car_ratings = {}
        for car in cars:
            result = db.query(
                func.avg(Reviews.rating).label('avg_rating'),
                func.count(Reviews.id).label('review_count')
            ).filter(
                Reviews.car_id == car.id,
                Reviews.is_approved == True,
                Reviews.is_hidden == False
            ).first()
            
            avg_rating = float(result.avg_rating) if result.avg_rating else 0.0
            review_count = result.review_count or 0
            car_ratings[car.id] = {
                "average": round(avg_rating, 1) if avg_rating > 0 else None,
                "count": review_count
            }
        
        # Check authentication using current_user dependency
        is_authenticated = not current_user.get("error")
        is_admin = current_user.get("isadmin", False)
        
        logger.debug(f"Rendering cars.html with {len(cars)} cars (page {page}) and {len(locations)} locations")
        
        # Convert locations to a format that matches the template
        # The Location model has a 'location' field, not 'name'
        locations_data = [{"name": loc.location, "location": loc.location} for loc in locations]
        
        return templates.TemplateResponse(
            "cars.html",
            {
                "request": request,
                "login_url": login_url,
                "cars": cars,
                "locations": locations_data,
                "brands": brands,
                "is_authenticated": is_authenticated,
                "is_admin": is_admin,
                "car_ratings": car_ratings,
                "pagination": pagination,
                "pickup_datetime": pickup_datetime,
                "end_datetime": end_datetime,
                "selected_location": location,
                "current_user": current_user
            }
        )
    except Exception as e:
        logger.error(f"Error rendering cars.html: {str(e)}", exc_info=True)
        # Fallback to basic response if template rendering fails
        access_token = request.cookies.get('access_token')
        is_authenticated = access_token is not None and access_token != ''
        return templates.TemplateResponse(
            "cars.html",
            {
                "request": request,
                "login_url": settings.LOGIN_URL,
                "cars": [],
                "locations": [],
                "brands": [],
                "is_authenticated": is_authenticated,
                "car_ratings": {},
                "pagination": {"page": 1, "total_pages": 1, "total": 0, "page_size": 12, "has_next": False, "has_prev": False},
                "pickup_datetime": None,
                "end_datetime": None,
                "selected_location": None
            }
        )


@app.get("/profile")
async def profile_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Render user profile page"""
    from fastapi.responses import RedirectResponse
    if current_user.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    from app.db.models import UserProfile
    user = db.query(UserProfile).filter(UserProfile.id == current_user.get("user_id")).first()
    
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Calculate KYC completion percentage
    kyc_fields = [user.aadhaar_front, user.aadhaar_back, user.drivinglicense_front, user.drivinglicense_back, user.phone, user.permanentaddress]
    filled_fields = [f for f in kyc_fields if f]
    kyc_percentage = int((len(filled_fields) / len(kyc_fields)) * 100)
    
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "current_user": user,
            "is_authenticated": True,
            "is_admin": user.isadmin,
            "kyc_percentage": kyc_percentage,
            "login_url": settings.LOGIN_URL
        }
    )


@app.get("/cars/{car_id}")
async def car_detail_page(
    request: Request,
    car_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Car detail page - render car_detail.html with car information"""
    from app.db.models import Cars, Reviews, Location
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload
    
    logger.info(f"Car detail page accessed for car_id: {car_id}")
    
    try:
        # Get the car
        car = db.query(Cars).filter(Cars.id == car_id, Cars.active == True).first()
        if not car:
            logger.warning(f"Car with ID {car_id} not found")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/cars", status_code=302)
        
        # Get car location
        location = db.query(Location).filter(Location.id == car.location_id).first()
        
        # Get car reviews
        reviews = db.query(Reviews).options(
            joinedload(Reviews.user)
        ).filter(
            Reviews.car_id == car_id,
            Reviews.is_approved == True,
            Reviews.is_hidden == False
        ).order_by(Reviews.created_at.desc()).all()
        
        # Calculate average rating
        result = db.query(
            func.avg(Reviews.rating).label('avg_rating'),
            func.count(Reviews.id).label('review_count')
        ).filter(
            Reviews.car_id == car_id,
            Reviews.is_approved == True,
            Reviews.is_hidden == False
        ).first()
        
        avg_rating = float(result.avg_rating) if result.avg_rating else 0.0
        review_count = result.review_count or 0
        
        # Get similar cars (same type, different car)
        similar_cars = db.query(Cars).filter(
            Cars.car_type == car.car_type,
            Cars.id != car_id,
            Cars.active == True
        ).limit(3).all()
        
        # Check authentication using current_user dependency
        is_authenticated = not current_user.get("error")
        is_admin = current_user.get("isadmin", False)
        
        # Convert reviews to dict format
        reviews_data = []
        for review in reviews:
            review_dict = {
                "id": review.id,
                "rating": review.rating,
                "comment": review.review_text or "",
                "user_firstname": review.user.firstname if review.user else "Anonymous",
                "user_lastname": review.user.lastname if review.user else "",
                "created_at": review.created_at.isoformat() if review.created_at else None
            }
            reviews_data.append(review_dict)
        
        logger.debug(f"Rendering car_detail.html for car {car.brand} {car.car_model}")
        
        return templates.TemplateResponse(
            "car_detail.html",
            {
                "request": request,
                "car": car,
                "location": location,
                "reviews": reviews_data,
                "avg_rating": round(avg_rating, 2),
                "review_count": review_count,
                "similar_cars": similar_cars,
                "is_authenticated": is_authenticated,
                "is_admin": is_admin,
                "login_url": settings.LOGIN_URL
            }
        )
    except Exception as e:
        logger.error(f"Error rendering car detail page: {str(e)}", exc_info=True)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/cars", status_code=302)


@app.get("/payment")
async def payment_page(
    request: Request,
    car_id: int = None,
    pickup_datetime: str = None,
    end_datetime: str = None,
    home_delivery: bool = False,
    delivery_address: Optional[str] = None,
    delivery_latitude: Optional[float] = None,
    delivery_longitude: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Payment page - render payment.html with dynamic data"""
    from fastapi.responses import RedirectResponse
    from app.db.models import Cars, UserProfile
    from app.services.payment_calculation import payment_calculation_service
    from app.services.kyc_service import kyc_service
    from datetime import datetime
    
    logger.info(f"Payment page accessed with car_id: {car_id}, pickup: {pickup_datetime}, end: {end_datetime}")
    
    try:
        # Check authentication
        if current_user.get("error"):
            # Store booking data and redirect to login
            if pickup_datetime and end_datetime:
                return_url = f"/payment?car_id={car_id}&pickup_datetime={pickup_datetime}&end_datetime={end_datetime}&home_delivery={home_delivery}"
                if delivery_address:
                    return_url += f"&delivery_address={delivery_address}"
                if delivery_latitude and delivery_longitude:
                    return_url += f"&delivery_latitude={delivery_latitude}&delivery_longitude={delivery_longitude}"
                return RedirectResponse(
                    url=f"{settings.LOGIN_URL}?return_url={return_url}",
                    status_code=302
                )
            return RedirectResponse(url="/", status_code=302)
        
        user_id = current_user.get("user_id")
        if not user_id:
            return RedirectResponse(url="/", status_code=302)
        
        # Get user profile with KYC documents
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not user:
            return RedirectResponse(url="/", status_code=302)
        
        # Get car data - car_id is required
        car = None
        if car_id:
            car = db.query(Cars).filter(Cars.id == car_id).first()
            if not car:
                logger.warning(f"Car with ID {car_id} not found in database")
                return RedirectResponse(url="/cars", status_code=302)
        else:
            logger.warning("No car_id provided in payment page - redirecting to cars page")
            return RedirectResponse(url="/cars", status_code=302)
        
        # Parse datetimes
        pickup_dt = None
        end_dt = None
        hours = 1
        
        if pickup_datetime and end_datetime:
            try:
                # Handle different datetime formats
                pickup_str = pickup_datetime.replace('Z', '+00:00') if 'Z' in pickup_datetime else pickup_datetime
                end_str = end_datetime.replace('Z', '+00:00') if 'Z' in end_datetime else end_datetime
                
                # Try parsing with timezone first
                try:
                    pickup_dt = datetime.fromisoformat(pickup_str)
                except ValueError:
                    # Try without timezone
                    pickup_dt = datetime.strptime(pickup_datetime, '%Y-%m-%dT%H:%M')
                
                try:
                    end_dt = datetime.fromisoformat(end_str)
                except ValueError:
                    # Try without timezone
                    end_dt = datetime.strptime(end_datetime, '%Y-%m-%dT%H:%M')
                
                duration = end_dt - pickup_dt
                hours = max(1, int(duration.total_seconds() / 3600))
            except Exception as e:
                logger.error(f"Error parsing datetimes: {str(e)}")
                hours = 1
        
        # Get missing KYC documents
        missing_documents = kyc_service.get_missing_documents(user)
        kyc_complete = kyc_service.is_kyc_complete(user)
        
        # Calculate pricing (default protection level 0 - no protection)
        pricing_breakdown = None
        if car:
            pricing_breakdown = payment_calculation_service.calculate_pricing_breakdown(
                base_price=float(car.base_price),
                damage_price=float(car.damage_price),
                hours=hours,
                damage_protection=0  # Default to 0 (no protection), can be changed by user
            )
        
        # Get car image
        car_image = "/static/img/landing.png"
        if car and car.images:
            image_urls = car.images.split(',') if ',' in car.images else [car.images]
            if image_urls:
                car_image = image_urls[0]
        
        return templates.TemplateResponse(
            "payment.html",
            {
                "request": request,
                "user": user,
                "car": car,
                "car_image": car_image,
                "pickup_datetime": pickup_datetime,
                "end_datetime": end_datetime,
                "hours": hours,
                "home_delivery": home_delivery,
                "delivery_address": delivery_address,
                "delivery_latitude": delivery_latitude,
                "delivery_longitude": delivery_longitude,
                "missing_documents": missing_documents,
                "kyc_complete": kyc_complete,
                "pricing_breakdown": pricing_breakdown,
                "is_authenticated": True,
                "is_admin": current_user.get("isadmin", False),
                "current_user": current_user
            }
        )
        
    except Exception as e:
        logger.error(f"Error rendering payment page: {str(e)}", exc_info=True)
        return RedirectResponse(url="/cars", status_code=302)


@app.get("/booking")
async def booking_page(
    request: Request,
    current_user: dict = Depends(auth.get_current_user)
):
    """Booking confirmation page - render booking.html"""
    logger.info("Booking page accessed")
    
    try:
        is_authenticated = not current_user.get("error")
        return templates.TemplateResponse(
            "booking.html",
            {
                "request": request,
                "is_authenticated": is_authenticated,
                "user_info": current_user if is_authenticated else None,
                "is_admin": current_user.get("isadmin", False) if is_authenticated else False,
                "login_url": settings.LOGIN_URL,
                "current_user": current_user
            }
        )
    except Exception as e:
        logger.error(f"Error rendering booking.html: {str(e)}", exc_info=True)
        return HTMLResponse(
            content=f"<h1>Error loading booking page</h1><p>{str(e)}</p>",
            status_code=500
        )


@app.get("/contact")
async def contact_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Contact page - render contact.html"""
    logger.info("Contact page accessed")
    
    try:
        # Check authentication using current_user dependency
        is_authenticated = not current_user.get("error")
        is_admin = current_user.get("isadmin", False)
        
        return templates.TemplateResponse(
            "contact.html",
            {
                "request": request,
                "is_authenticated": is_authenticated,
                "is_admin": is_admin,
                "login_url": settings.LOGIN_URL,
                "current_user": current_user
            }
        )
    except Exception as e:
        logger.error(f"Error rendering contact.html: {str(e)}", exc_info=True)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<h1>Error loading contact page</h1>",
            status_code=500
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


