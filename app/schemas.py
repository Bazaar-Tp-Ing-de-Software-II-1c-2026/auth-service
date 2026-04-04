from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, HttpUrl
from typing import Optional
import re

def normalize_email(v: EmailStr) -> str:
    return v.strip().lower()

def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")

    if not re.search(r"[A-Z]", v):
        raise ValueError("Debe contener al menos una mayúscula")

    if not re.search(r"[a-z]", v):
        raise ValueError("Debe contener al menos una minúscula")

    if not re.search(r"[0-9]", v):
        raise ValueError("Debe contener al menos un número")

    return v


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
        return normalize_email(v)

    @field_validator("password")
    @classmethod
    def password_validator(cls, v: str) -> str:
        return validate_password_strength(v)


class UserLogin(BaseModel):
    identifier: str  # Puede ser email o username
    password: str

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, v: str) -> str:
        # Solo normalizamos si parece un email
        if "@" in v:
            return v.strip().lower()
        return v.strip()

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, v: EmailStr) -> str:
        return normalize_email(v)


class ResendVerificationEmailRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, v: EmailStr) -> str:
        return normalize_email(v)


class ResetPassword(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_validator(cls, v: str) -> str:
        return validate_password_strength(v)


class GoogleLoginRequest(BaseModel):
    id_token: str


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, v: EmailStr) -> str:
        return normalize_email(v)


class ResetPasswordWithCodeRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

    @field_validator("email")
    @classmethod
    def email_to_lower(cls, v: EmailStr) -> str:
        return normalize_email(v)

    @field_validator("new_password")
    @classmethod
    def password_validator(cls, v: str) -> str:
        return validate_password_strength(v)

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
            raise ValueError("El nombre no puede estar vacío")
        if len(normalized) > 50:
            raise ValueError("El nombre no puede superar 50 caracteres")
        return normalized

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = v.strip()
        if len(normalized) > 280:
            raise ValueError("La descripción no puede superar 280 caracteres")
        return normalized or None