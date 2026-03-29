from pydantic import BaseModel, EmailStr
from typing import Optional


# User signs up with email, password and full name
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str
    first_name: str
    last_name: str

# Information about the user that is returned when they log in or when their information is requested
class UserOut(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    blocked: bool = False
    username: str

    class Config:
        from_attributes = True

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str