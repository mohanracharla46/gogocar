"""
Admin routes for user management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.schemas.user import UserResponse, UserUpdate, KYCApprove, KYCReject
from app.routes.admin.dependencies import require_admin
from app.utils.pagination import PaginatedResponse
from app.db.models import UserProfile, KYCStatus
from app.core.logging_config import logger

router = APIRouter(
    prefix="/admin/api/users",
    tags=["admin-users"]
)


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    kyc_status: Optional[KYCStatus] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all users with pagination and filters"""
    skip = (page - 1) * page_size
    
    # Build query
    query = db.query(UserProfile)
    
    # Apply filters
    if search:
        search_filter = or_(
            UserProfile.firstname.ilike(f"%{search}%"),
            UserProfile.lastname.ilike(f"%{search}%"),
            UserProfile.email.ilike(f"%{search}%"),
            UserProfile.username.ilike(f"%{search}%"),
            UserProfile.phone.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    if kyc_status:
        query = query.filter(UserProfile.kyc_status == kyc_status)
    
    if is_active is not None:
        query = query.filter(UserProfile.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    users = query.order_by(UserProfile.created_at.desc()).offset(skip).limit(page_size).all()
    
    return PaginatedResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=page * page_size < total,
        has_prev=page > 1
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get user by ID"""
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update user"""
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    update_data = user_data.dict(exclude_unset=True)
    
    # Handle KYC status changes
    if 'kyc_status' in update_data:
        new_status = update_data['kyc_status']
        from datetime import datetime
        
        if new_status == KYCStatus.APPROVED and user.kyc_status != KYCStatus.APPROVED:
            # Approving KYC
            user.kyc_approved_by = current_user["user_id"]
            user.kyc_approved_at = datetime.now()
            user.kyc_rejection_reason = None
        elif new_status == KYCStatus.REJECTED and user.kyc_status != KYCStatus.REJECTED:
            # Rejecting KYC
            user.kyc_approved_by = current_user["user_id"]
            if 'kyc_rejection_reason' not in update_data or not update_data.get('kyc_rejection_reason'):
                # If no reason provided, keep existing or set default
                if not user.kyc_rejection_reason:
                    update_data['kyc_rejection_reason'] = 'Rejected by admin'
        elif new_status == KYCStatus.PENDING:
            # Resetting to pending clears approval info
            user.kyc_approved_by = None
            user.kyc_approved_at = None
            user.kyc_rejection_reason = None
    
    # Update all fields
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user_id} updated by admin {current_user['user_id']}")
    return user


@router.post("/{user_id}/kyc/approve", response_model=UserResponse)
async def approve_kyc(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Approve user KYC"""
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.kyc_status != KYCStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"KYC status must be PENDING to approve. Current status: {user.kyc_status.value}"
        )
    
    from datetime import datetime
    user.kyc_status = KYCStatus.APPROVED
    user.kyc_approved_by = current_user["user_id"]
    user.kyc_approved_at = datetime.now()
    user.kyc_rejection_reason = None
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"KYC approved for user {user_id} by admin {current_user['user_id']}")
    return user


@router.post("/{user_id}/kyc/reject", response_model=UserResponse)
async def reject_kyc(
    user_id: int,
    reject_data: KYCReject,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Reject user KYC"""
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.kyc_status != KYCStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"KYC status must be PENDING to reject. Current status: {user.kyc_status.value}"
        )
    
    user.kyc_status = KYCStatus.REJECTED
    user.kyc_approved_by = current_user["user_id"]
    user.kyc_rejection_reason = reject_data.rejection_reason
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"KYC rejected for user {user_id} by admin {current_user['user_id']}")
    return user


@router.post("/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Toggle user active status"""
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deactivating yourself
    if user.id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user_id} active status toggled to {user.is_active} by admin {current_user['user_id']}")
    return user

