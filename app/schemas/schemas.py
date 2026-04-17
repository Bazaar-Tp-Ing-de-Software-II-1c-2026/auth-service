from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, HttpUrl, StringConstraints
from typing import Optional, Annotated
import re


# -------------------------
# HELPERS (internos)
# -------------------------

def _normalize_email(v: EmailStr) -> str:
    return v.strip().lower()


def _validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one number")
    return v


# -------------------------
# AUTH
# -------------------------

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str
    first_name: str
    last_name: str

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, v: EmailStr) -> str:
        return _normalize_email(v)

    @field_validator("password")
    @classmethod
    def password_validator(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserLogin(BaseModel):
    identifier: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, v: str) -> str:
        if "@" in v:
            return v.lower()

        return v


class GoogleLoginRequest(BaseModel):
    id_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, v: EmailStr) -> str:
        return _normalize_email(v)


class ResendVerificationEmailRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, v: EmailStr) -> str:
        return _normalize_email(v)


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, v: EmailStr) -> str:
        return _normalize_email(v)


class ResetPasswordWithCodeRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, v: EmailStr) -> str:
        return _normalize_email(v)

    @field_validator("new_password")
    @classmethod
    def password_validator(cls, v: str) -> str:
        return _validate_password_strength(v)


class ResetPassword(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_validator(cls, v: str) -> str:
        return _validate_password_strength(v)


# -------------------------
# USER
# -------------------------

class UserBase(BaseModel):
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    description: Optional[str] = None
    profile_picture_url: Optional[str] = None


class UserOut(UserBase):
    id: int
    email: EmailStr
    role: str
    blocked: bool = False
    is_verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserPublicOut(UserBase):
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    description: Optional[str] = None
    profile_picture_url: Optional[HttpUrl] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = v.strip()
        if not normalized:
            raise ValueError("Name cannot be empty")
        if len(normalized) > 50:
            raise ValueError("Name cannot exceed 50 characters")
        return normalized

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = v.strip()
        if len(normalized) > 280:
            raise ValueError("Description cannot exceed 280 characters")
        return normalized or None