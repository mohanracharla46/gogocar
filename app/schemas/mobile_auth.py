from typing import Optional
from pydantic import BaseModel, EmailStr
from app.schemas.user import UserResponse

class MobileLoginRequest(BaseModel):
    username: str
    password: str

class MobileSignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    firstname: str
    lastname: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
