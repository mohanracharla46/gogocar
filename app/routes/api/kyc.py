"""
Mobile KYC upload endpoint
POST /api/mobile/kyc/upload
"""
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import KYCStatus, UserProfile
from app.services.kyc_service import kyc_service
from app.routes.mobile import get_current_user
from app.core.logging_config import logger

router = APIRouter(tags=["Mobile KYC"])


@router.post("/upload")
async def mobile_kyc_upload(
    aadhaar_front: UploadFile = File(...),
    aadhaar_back: UploadFile = File(...),
    drivinglicense_front: UploadFile = File(None),
    drivinglicense_back: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Upload KYC documents for mobile users.
    Accepts aadhaar_front and aadhaar_back (required).
    Optionally accepts drivinglicense_front and drivinglicense_back.
    Stores files using the same storage backend as the web endpoint.
    Sets kyc_status to PENDING and returns JSON only.
    """
    user_id = current_user.id

    # --- Upload aadhaar_front (required) ---
    af_url = await kyc_service.upload_kyc_document(db, user_id, "aadhaar_front", aadhaar_front)
    if not af_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aadhaar_front upload failed. Check file format (jpg/jpeg/png/pdf) or size (max 10 MB).",
        )

    # --- Upload aadhaar_back (required) ---
    ab_url = await kyc_service.upload_kyc_document(db, user_id, "aadhaar_back", aadhaar_back)
    if not ab_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aadhaar_back upload failed. Check file format (jpg/jpeg/png/pdf) or size (max 10 MB).",
        )

    # --- Upload drivinglicense_front (optional) ---
    if drivinglicense_front and drivinglicense_front.filename:
        dlf_url = await kyc_service.upload_kyc_document(db, user_id, "dl_front", drivinglicense_front)
        if not dlf_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="drivinglicense_front upload failed. Check file format (jpg/jpeg/png/pdf) or size (max 10 MB).",
            )

    # --- Upload drivinglicense_back (optional) ---
    if drivinglicense_back and drivinglicense_back.filename:
        dlb_url = await kyc_service.upload_kyc_document(db, user_id, "dl_back", drivinglicense_back)
        if not dlb_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="drivinglicense_back upload failed. Check file format (jpg/jpeg/png/pdf) or size (max 10 MB).",
            )

    # --- Force kyc_status to PENDING and update updated_at ---
    try:
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.kyc_status = KYCStatus.PENDING
        user.updated_at = datetime.now()
        db.commit()
        logger.info(f"Mobile KYC uploaded for user {user_id}. Status set to PENDING.")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Mobile KYC status update error for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="KYC files uploaded but failed to update status. Please contact support.",
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "KYC uploaded successfully",
            "kyc_status": "PENDING",
        },
    )
