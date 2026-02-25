"""
Mobile KYC endpoints
  POST /api/mobile/kyc/upload  – upload documents, set status PENDING
  GET  /api/mobile/kyc/status  – read current KYC status + rejection reason
"""
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import KYCStatus, UserProfile
from app.services.kyc_service import kyc_service
from app.routes.mobile import get_current_user
from app.schemas.mobile import MobileKYCUploadResponse, MobileKYCStatusResponse
from app.core.logging_config import logger

router = APIRouter(tags=["Mobile KYC"])


@router.post("/upload", response_model=MobileKYCUploadResponse)
async def mobile_kyc_upload(
    aadhaar_front: UploadFile = File(...),
    aadhaar_back: UploadFile = File(...),
    drivinglicense_front: UploadFile = File(None),
    drivinglicense_back: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Upload KYC documents (multipart/form-data). JWT required.
    aadhaar_front and aadhaar_back are required.
    drivinglicense_front and drivinglicense_back are optional.
    Sets kyc_status to PENDING and returns JSON only.
    """
    user_id = current_user.id

    # Upload aadhaar_front (required)
    af_url = await kyc_service.upload_kyc_document(db, user_id, "aadhaar_front", aadhaar_front)
    if not af_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aadhaar_front upload failed. Allowed formats: jpg, jpeg, png, pdf. Max size: 10 MB.",
        )

    # Upload aadhaar_back (required)
    ab_url = await kyc_service.upload_kyc_document(db, user_id, "aadhaar_back", aadhaar_back)
    if not ab_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aadhaar_back upload failed. Allowed formats: jpg, jpeg, png, pdf. Max size: 10 MB.",
        )

    # Upload drivinglicense_front (optional)
    if drivinglicense_front and drivinglicense_front.filename:
        dlf_url = await kyc_service.upload_kyc_document(db, user_id, "dl_front", drivinglicense_front)
        if not dlf_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="drivinglicense_front upload failed. Allowed formats: jpg, jpeg, png, pdf. Max size: 10 MB.",
            )

    # Upload drivinglicense_back (optional)
    if drivinglicense_back and drivinglicense_back.filename:
        dlb_url = await kyc_service.upload_kyc_document(db, user_id, "dl_back", drivinglicense_back)
        if not dlb_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="drivinglicense_back upload failed. Allowed formats: jpg, jpeg, png, pdf. Max size: 10 MB.",
            )

    # Force kyc_status = PENDING and refresh updated_at
    try:
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.kyc_status = KYCStatus.PENDING
        user.updated_at = datetime.now()
        db.commit()
        logger.info(f"Mobile KYC uploaded for user {user_id}. Status → PENDING.")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Mobile KYC status update error for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Files uploaded but status update failed. Contact support.",
        )

    return {"success": True, "kyc_status": "PENDING"}


@router.get("/status", response_model=MobileKYCStatusResponse)
def mobile_kyc_status(
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Return the current KYC status for the logged-in user. JWT required.
    Includes rejection reason when status is REJECTED.
    """
    kyc_val = current_user.kyc_status
    kyc_str = kyc_val.value if hasattr(kyc_val, "value") else str(kyc_val)

    reason = None
    if kyc_str == "REJECTED":
        reason = current_user.kyc_rejection_reason

    return {"kyc_status": kyc_str, "reason": reason}
