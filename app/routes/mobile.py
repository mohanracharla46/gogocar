from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import UserProfile, KYCStatus
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.schemas.mobile_auth import MobileLoginRequest, MobileSignupRequest, Token
from app.schemas.mobile import (
    MobileProfileResponse,
    MobileProfileUpdate,
    MobileChangePasswordRequest,
    MobileMessageResponse,
)

router = APIRouter(tags=["Mobile Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/mobile/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserProfile:
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("sub")
    user = db.query(UserProfile).filter(UserProfile.username == username).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=Token)
async def signup(request: MobileSignupRequest, db: Session = Depends(get_db)):
    """Register a new mobile user. Returns JWT token."""
    existing_user = db.query(UserProfile).filter(
        (UserProfile.username == request.username) | (UserProfile.email == request.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )

    new_user = UserProfile(
        username=request.username,
        email=request.email,
        firstname=request.firstname,
        lastname=request.lastname,
        hashed_password=get_password_hash(request.password),
        is_active=True,
        isadmin=False,
        kyc_status=KYCStatus.NOT_SUBMITTED
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.username, "email": new_user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": new_user}


@router.post("/login", response_model=Token)
async def login(request: MobileLoginRequest, db: Session = Depends(get_db)):
    """Login with username + password. Returns JWT token."""
    user = db.query(UserProfile).filter(UserProfile.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    access_token = create_access_token(data={"sub": user.username, "email": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=MobileProfileResponse)
def get_profile(current_user: UserProfile = Depends(get_current_user)):
    """Return the logged-in user's profile. JWT required."""
    kyc_val = current_user.kyc_status
    return {
        "id": current_user.id,
        "username": current_user.username,
        "firstname": current_user.firstname,
        "lastname": current_user.lastname,
        "email": current_user.email,
        "phone": current_user.phone,
        "permanentaddress": current_user.permanentaddress,
        "kyc_status": kyc_val.value if hasattr(kyc_val, "value") else str(kyc_val),
        "created_at": current_user.created_at,
        "aadhaar_front": current_user.aadhaar_front,
        "aadhaar_back": current_user.aadhaar_back,
        "drivinglicense_front": current_user.drivinglicense_front,
        "drivinglicense_back": current_user.drivinglicense_back,
    }


@router.put("/profile", response_model=MobileProfileResponse)
async def update_profile(
    body: MobileProfileUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Update firstname, lastname, phone, or permanentaddress. JWT Required.
    Implements production-ready partial update logic.
    """
    user = db.query(UserProfile).filter(UserProfile.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Safe partial update logic
    update_data = body.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        if value is not None:
            # Specific validation for phone
            if key == "phone":
                phone = str(value).strip()
                if not phone.isdigit() or len(phone) not in (10, 12):
                    raise HTTPException(status_code=400, detail="Phone must be digits only and length 10 or 12")
                user.phone = phone
            else:
                setattr(user, key, value.strip() if isinstance(value, str) else value)

    user.updated_at = datetime.now()
    
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Profile update failed")

    kyc_val = user.kyc_status
    return {
        "id": user.id,
        "username": user.username,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "email": user.email,
        "phone": user.phone,
        "permanentaddress": user.permanentaddress,
        "kyc_status": kyc_val.value if hasattr(kyc_val, "value") else str(kyc_val),
        "created_at": user.created_at,
        "aadhaar_front": user.aadhaar_front,
        "aadhaar_back": user.aadhaar_back,
        "drivinglicense_front": user.drivinglicense_front,
        "drivinglicense_back": user.drivinglicense_back,
    }


@router.put("/change-password", response_model=MobileMessageResponse)
async def change_password(
    body: MobileChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Update user password. JWT required.
    Verifies old password and hashes new password.
    """
    user = db.query(UserProfile).filter(UserProfile.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verify old password
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )

    # Hash new password and update
    user.hashed_password = get_password_hash(body.new_password)
    user.updated_at = datetime.now()

    try:
        db.commit()
        return {"message": "Password updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
