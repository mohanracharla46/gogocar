from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import UserProfile, KYCStatus
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.schemas.mobile_auth import MobileLoginRequest, MobileSignupRequest, Token

router = APIRouter(tags=["Mobile Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/mobile/login")



def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    print("Received token:", token)

    payload = decode_access_token(token)
    print("Decoded payload:", payload)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    username: str = payload.get("sub")
    print("Username from token:", username)

    user = db.query(UserProfile).filter(UserProfile.username == username).first()
    print("User found:", user)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.get("/me")
def get_me(current_user: UserProfile = Depends(get_current_user)):
    return current_user

@router.post("/signup", response_model=Token)
async def signup(request: MobileSignupRequest, db: Session = Depends(get_db)):
    # Check existing user
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
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user
    }

@router.post("/login", response_model=Token)
async def login(request: MobileLoginRequest, db: Session = Depends(get_db)):
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
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }
