"""
Customer-facing ticket routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models import SupportTicket, UserProfile, Orders, TicketStatus, TicketMessage
from app.routes.auth import get_current_user
from app.schemas.ticket import TicketCreate, TicketResponse
from app.core.logging_config import logger
from app.core.templates import templates
from app.utils.pagination import paginate_query

router = APIRouter(
    prefix="/tickets",
    tags=["tickets"]
)


def generate_ticket_number(db: Session) -> str:
    """Generate unique ticket number"""
    import random
    import string
    
    while True:
        # Format: TKT-YYYYMMDD-XXXX (4 random alphanumeric)
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        ticket_number = f"TKT-{date_str}-{random_str}"
        
        # Check if exists
        existing = db.query(SupportTicket).filter(
            SupportTicket.ticket_number == ticket_number
        ).first()
        
        if not existing:
            return ticket_number


@router.get("", response_class=HTMLResponse)
async def view_tickets(
    request: Request,
    page: int = 1,
    page_size: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    View user's support tickets
    
    Args:
        request: FastAPI request object
        page: Page number
        page_size: Items per page
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Template response with tickets list
    """
    if current_user.get("error"):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        user = db.query(UserProfile).filter(
            UserProfile.id == current_user["user_id"]
        ).first()
        
        if not user:
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
        # Get user's tickets
        query = db.query(SupportTicket).filter(
            SupportTicket.user_id == user.id
        ).order_by(SupportTicket.created_at.desc())
        
        # Validate and limit page_size
        page_size = min(max(1, page_size), 100)  # Between 1 and 100
        
        tickets, pagination = paginate_query(query, page=page, page_size=page_size)
        
        return templates.TemplateResponse(
            "tickets/tickets_list.html",
            {
                "request": request,
                "tickets": tickets,
                "pagination": pagination,
                "user": user
            }
        )
    except Exception as e:
        logger.error(f"Error viewing tickets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load tickets"
        )


@router.get("/search-order/{order_id}")
async def search_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Search for an order by ID (only returns if belongs to current user)
    
    Args:
        order_id: Order ID to search
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Order details with car information
    """
    if current_user.get("error"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    user = db.query(UserProfile).filter(
        UserProfile.id == current_user["user_id"]
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get order and verify it belongs to user
    from app.db.models import Cars
    from sqlalchemy.orm import joinedload
    
    order = db.query(Orders).options(
        joinedload(Orders.car)
    ).filter(
        Orders.id == order_id,
        Orders.user_id == user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or does not belong to you"
        )
    
    return {
        "id": order.id,
        "car_id": order.car_id,
        "car_brand": order.car.brand if order.car else None,
        "car_model": order.car.car_model if order.car else None,
        "registration_number": order.car.registration_number if order.car else None,
        "start_time": order.start_time.isoformat() if order.start_time else None
    }


@router.get("/{ticket_id}", response_class=HTMLResponse)
async def view_ticket_detail(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    View ticket details
    
    Args:
        request: FastAPI request object
        ticket_id: Ticket ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Template response with ticket details
    """
    if current_user.get("error"):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        user = db.query(UserProfile).filter(
            UserProfile.id == current_user["user_id"]
        ).first()
        
        from sqlalchemy.orm import joinedload
        
        ticket = db.query(SupportTicket).options(
            joinedload(SupportTicket.messages).joinedload(TicketMessage.sender)
        ).filter(
            SupportTicket.id == ticket_id,
            SupportTicket.user_id == user.id
        ).first()
        
        if not ticket:
            return RedirectResponse(url="/tickets", status_code=status.HTTP_302_FOUND)
        
        return templates.TemplateResponse(
            "tickets/ticket_detail.html",
            {
                "request": request,
                "ticket": ticket,
                "user": user
            }
        )
    except Exception as e:
        logger.error(f"Error viewing ticket detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load ticket"
        )


@router.post("/{ticket_id}/reply")
async def customer_reply_to_ticket(
    request: Request,
    ticket_id: int,
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Customer reply to a ticket"""
    from app.utils.s3_service import s3_service
    from datetime import datetime
    import os
    
    if current_user.get("error"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    user = db.query(UserProfile).filter(
        UserProfile.id == current_user["user_id"]
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get ticket and verify it belongs to user
    from sqlalchemy.orm import joinedload
    
    ticket = db.query(SupportTicket).options(
        joinedload(SupportTicket.user)
    ).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.user_id == user.id
    ).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found or does not belong to you"
        )
    
    # Handle file upload if provided
    file_url = None
    if file:
        # Check file size (max 5MB for email attachments)
        MAX_EMAIL_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > MAX_EMAIL_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of 5MB. Current size: {file_size / 1024 / 1024:.2f}MB"
            )
        
        # Check if it's an image
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only image files are allowed. Allowed extensions: {', '.join(allowed_extensions)}"
            )
        
        # Reset file pointer and upload
        await file.seek(0)
        try:
            file_url = await s3_service.upload_file(
                file=file,
                folder="ticket-replies",
                object_name=f"{ticket_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
            )
        except Exception as e:
            logger.error(f"Error uploading file for ticket {ticket_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file"
            )
    
    # Store reply as a message
    reply_message = TicketMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        is_admin=False,
        message=message,
        attachment_url=file_url
    )
    db.add(reply_message)
    
    # Update ticket
    ticket.updated_at = datetime.now()
    db.commit()
    db.refresh(ticket)
    
    logger.info(f"Customer reply stored for ticket {ticket.ticket_number} by user {user.id}")
    
    return JSONResponse({
        "success": True,
        "message": "Reply sent successfully",
        "file_url": file_url
    })


@router.post("/create")
async def create_ticket(
    request: Request,
    subject: str = Form(...),
    description: str = Form(...),
    order_id: Optional[int] = Form(None),
    priority: str = Form("MEDIUM"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new support ticket
    
    Args:
        request: FastAPI request object
        subject: Ticket subject
        description: Ticket description
        order_id: Optional order ID
        priority: Ticket priority
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Redirect to tickets page
    """
    if current_user.get("error"):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        user = db.query(UserProfile).filter(
            UserProfile.id == current_user["user_id"]
        ).first()
        
        if not user:
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
        # Validate order_id if provided - verify it belongs to user
        if order_id:
            order = db.query(Orders).filter(
                Orders.id == order_id,
                Orders.user_id == user.id
            ).first()
            if not order:
                return RedirectResponse(url="/tickets?error=invalid_order", status_code=status.HTTP_302_FOUND)
        
        # Generate ticket number
        ticket_number = generate_ticket_number(db)
        
        # Create ticket
        ticket = SupportTicket(
            ticket_number=ticket_number,
            user_id=user.id,
            order_id=order_id,
            subject=subject,
            description=description,
            priority=priority,
            status=TicketStatus.OPEN
        )
        
        db.add(ticket)
        db.flush()  # Get ticket ID without committing
        
        # Create initial message from customer
        initial_message = TicketMessage(
            ticket_id=ticket.id,
            sender_id=user.id,
            is_admin=False,
            message=description
        )
        db.add(initial_message)
        db.commit()
        db.refresh(ticket)
        
        logger.info(f"Ticket created: {ticket_number} by user {user.id}")
        
        # Send WebSocket notification to admins
        try:
            from app.utils.websocket_manager import websocket_manager
            await websocket_manager.send_notification(
                notification_type="ticket",
                data={
                    "ticket_id": ticket.id,
                    "ticket_number": ticket.ticket_number,
                    "user_name": f"{user.firstname} {user.lastname}".strip() or user.username,
                    "subject": ticket.subject,
                    "priority": ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority)
                }
            )
        except Exception as e:
            logger.error(f"Error sending WebSocket notification for ticket: {str(e)}")
            # Don't fail ticket creation if notification fails
        
        return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Error creating ticket: {str(e)}")
        db.rollback()
        return RedirectResponse(url="/tickets?error=create_failed", status_code=status.HTTP_302_FOUND)

