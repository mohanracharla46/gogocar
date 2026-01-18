"""
Admin API routes for ticket management
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from fastapi.responses import JSONResponse

from app.db.session import get_db
from app.db.models import SupportTicket, UserProfile, TicketStatus, TicketMessage
from app.routes.admin.dependencies import require_admin
from app.schemas.ticket import TicketResponse, TicketUpdate
from app.core.logging_config import logger
from app.utils.pagination import paginate_query, PaginatedResponse

router = APIRouter(
    prefix="/admin/api/tickets",
    tags=["admin-tickets"]
)


def enrich_ticket(ticket: SupportTicket) -> dict:
    """Enrich ticket with user details"""
    ticket_dict = {
        "id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "user_id": ticket.user_id,
        "order_id": ticket.order_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
        "assigned_to": ticket.assigned_to,
        "resolved_at": ticket.resolved_at,
        "resolved_by": ticket.resolved_by,
        "resolution_notes": ticket.resolution_notes,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "user_firstname": ticket.user.firstname if ticket.user else None,
        "user_lastname": ticket.user.lastname if ticket.user else None,
    }
    return ticket_dict


@router.get("", response_model=PaginatedResponse[TicketResponse])
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all tickets with pagination and filters"""
    query = db.query(SupportTicket).options(
        joinedload(SupportTicket.user)
    ).order_by(SupportTicket.created_at.desc())
    
    # Apply filters
    if status:
        try:
            status_enum = TicketStatus(status.upper())
            query = query.filter(SupportTicket.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    if priority:
        query = query.filter(SupportTicket.priority == priority.upper())
    
    tickets, pagination = paginate_query(query, page=page, page_size=page_size)
    
    # Enrich tickets with user details
    enriched_tickets = []
    for ticket in tickets:
        ticket_data = enrich_ticket(ticket)
        enriched_tickets.append(TicketResponse(**ticket_data))
    
    return PaginatedResponse(
        items=enriched_tickets,
        total=pagination.total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=pagination.total_pages,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get single ticket details"""
    ticket = db.query(SupportTicket).options(
        joinedload(SupportTicket.user)
    ).filter(SupportTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    ticket_data = enrich_ticket(ticket)
    return TicketResponse(**ticket_data)


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    update_data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update ticket"""
    ticket = db.query(SupportTicket).options(
        joinedload(SupportTicket.user)
    ).filter(SupportTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Update fields from request body
    update_dict = update_data.model_dump(exclude_unset=True)
    
    if 'status' in update_dict and update_dict['status'] is not None:
        ticket.status = update_dict['status']
        
        # Set resolved_at when status changes to RESOLVED or CLOSED
        if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] and not ticket.resolved_at:
            from datetime import datetime
            ticket.resolved_at = datetime.now()
            ticket.resolved_by = current_user["user_id"]
        elif ticket.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            ticket.resolved_at = None
            ticket.resolved_by = None
    
    if 'priority' in update_dict and update_dict['priority'] is not None:
        ticket.priority = update_dict['priority'].upper()
    
    if 'assigned_to' in update_dict and update_dict['assigned_to'] is not None:
        # Verify assigned user exists and is admin
        assigned_user = db.query(UserProfile).filter(
            UserProfile.id == update_dict['assigned_to'],
            UserProfile.isadmin == True
        ).first()
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user must be an admin"
            )
        ticket.assigned_to = update_dict['assigned_to']
    
    if 'resolution_notes' in update_dict and update_dict['resolution_notes'] is not None:
        ticket.resolution_notes = update_dict['resolution_notes']
    
    db.commit()
    db.refresh(ticket)
    
    logger.info(f"Ticket {ticket_id} updated by admin {current_user['user_id']}")
    
    ticket_data = enrich_ticket(ticket)
    return TicketResponse(**ticket_data)


@router.post("/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: int,
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Reply to a ticket - sends email to customer"""
    from app.utils.s3_service import s3_service
    from app.utils.email_service import email_service
    from datetime import datetime
    import os
    
    ticket = db.query(SupportTicket).options(
        joinedload(SupportTicket.user)
    ).filter(SupportTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if not ticket.user or not ticket.user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket user email not found"
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
    
    # Update ticket status if needed
    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.assigned_to = current_user["user_id"]
    
    # Store reply as a message
    reply_message = TicketMessage(
        ticket_id=ticket.id,
        sender_id=current_user["user_id"],
        is_admin=True,
        message=message,
        attachment_url=file_url
    )
    db.add(reply_message)
    
    # Update ticket
    ticket.updated_at = datetime.now()
    db.commit()
    db.refresh(ticket)
    
    # Send email to customer
    try:
        user_name = f"{ticket.user.firstname} {ticket.user.lastname}".strip() or ticket.user.username or "Customer"
        
        # Prepare email content
        subject = f"Re: {ticket.subject} - Ticket #{ticket.ticket_number}"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Ticket Reply</h1>
            </div>
            <div style="background: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
                <p style="margin: 0 0 20px 0;">Dear <strong>{user_name}</strong>,</p>
                <p style="margin: 0 0 20px 0;">We have received your support ticket and here is our response:</p>
                
                <div style="background: #f9fafb; border-left: 4px solid #3b82f6; padding: 20px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; white-space: pre-wrap;">{message}</p>
                </div>
                
                {f'<div style="margin: 20px 0;"><p style="margin: 0 0 10px 0;"><strong>Attachment:</strong></p><a href="{file_url}" style="color: #3b82f6; text-decoration: none;">View Image</a></div>' if file_url else ''}
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 0 0 10px 0; font-size: 14px; color: #6b7280;">
                        <strong>Ticket Details:</strong><br>
                        Ticket Number: <strong>{ticket.ticket_number}</strong><br>
                        Subject: {ticket.subject}<br>
                        Status: {ticket.status.value}
                    </p>
                </div>
                
                <p style="margin: 30px 0 0 0; color: #6b7280; font-size: 14px;">
                    If you have any further questions, please reply to this email or visit your ticket page.
                </p>
                
                <p style="margin: 20px 0 0 0;">
                    Best regards,<br>
                    <strong>The GoGoCar Support Team</strong>
                </p>
            </div>
            <div style="text-align: center; margin-top: 20px; color: #9ca3af; font-size: 12px;">
                <p>© {datetime.now().year} GoGoCar. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
Dear {user_name},

We have received your support ticket and here is our response:

{message}

{f'Attachment: {file_url}' if file_url else ''}

Ticket Details:
Ticket Number: {ticket.ticket_number}
Subject: {ticket.subject}
Status: {ticket.status.value}

If you have any further questions, please reply to this email or visit your ticket page.

Best regards,
The GoGoCar Support Team
        """
        
        email_service.send_email(
            to_email=ticket.user.email,
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )
        
        logger.info(f"Reply email sent to {ticket.user.email} for ticket {ticket.ticket_number}")
    except Exception as e:
        logger.error(f"Error sending reply email for ticket {ticket_id}: {str(e)}", exc_info=True)
        # Don't fail the reply if email fails, but log it
    
    return JSONResponse({
        "success": True,
        "message": "Reply sent successfully",
        "file_url": file_url
    })

