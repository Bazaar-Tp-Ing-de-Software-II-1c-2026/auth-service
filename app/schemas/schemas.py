from datetime import datetime
from typing import Any, Optional, Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    field_validator,
    HttpUrl,
    StringConstraints,
)
from pydantic_core import PydanticCustomError
import re

# -------------------------
# HELPERS (internos)
# -------------------------


def _normalize_email(v: EmailStr) -> str:
    return v.strip().lower()


def _validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise PydanticCustomError(
            "password_too_short",
            "Password must be at least 8 characters long",
        )
    if not re.search(r"[A-Z]", v):
        raise PydanticCustomError(
            "password_missing_uppercase",
            "Password must contain at least one uppercase letter",
        )
    if not re.search(r"[a-z]", v):
        raise PydanticCustomError(
            "password_missing_lowercase",
            "Password must contain at least one lowercase letter",
        )
    if not re.search(r"[0-9]", v):
        raise PydanticCustomError(
            "password_missing_number",
            "Password must contain at least one number",
        )
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
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    first_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    last_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

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
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None
    shipping_phone: Optional[str] = None


class UserPublicOut(UserBase):
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserOut(UserBase):
    id: int
    email: EmailStr
    role: str
    blocked: bool = False
    is_verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class AdminUserListItem(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime
    status: str
    role: Optional[str] = "user"
    profile_picture_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PaginatedAdminUsersResponse(BaseModel):
    data: list[AdminUserListItem]
    total: int
    page: int
    limit: int


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    description: Optional[str] = None
    profile_picture_url: Optional[HttpUrl] = None
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None
    shipping_phone: Optional[str] = None

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

    @field_validator(
        "shipping_address", "shipping_city", "shipping_state", "shipping_country"
    )
    @classmethod
    def validate_address_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = v.strip()
        if len(normalized) > 200:
            raise ValueError("Address field cannot exceed 200 characters")
        return normalized or None

    @field_validator("shipping_postal_code")
    @classmethod
    def validate_postal_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = v.strip()
        if len(normalized) > 20:
            raise ValueError("Postal code cannot exceed 20 characters")
        return normalized or None

    @field_validator("shipping_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = v.strip()
        if len(normalized) > 20:
            raise ValueError("Phone number cannot exceed 20 characters")
        return normalized or None


# -------------------------
# NOTIFICATIONS
# -------------------------


class NotificationCreateRequest(BaseModel):
    user_id: int
    notification_type: str
    title: str
    body: str
    data: dict[str, Any] | None = None
    source: str = "product-service"


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_type: str
    title: str
    body: str
    data: dict[str, Any] | None = None
    source: str
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    data: list[NotificationResponse]
    total: int


# -------------------------
# PIN AUTHENTICATION
# -------------------------


class PINSetupRequest(BaseModel):
    pin: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=6, max_length=8)
    ]
    device_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not v.isdigit():
            raise PydanticCustomError(
                "pin_not_numeric",
                "PIN must contain only numbers",
            )
        if len(v) < 6:
            raise PydanticCustomError(
                "pin_too_short",
                "PIN must be at least 6 digits",
            )
        if len(v) > 8:
            raise PydanticCustomError(
                "pin_too_long",
                "PIN cannot exceed 8 digits",
            )
        return v


class PINLoginRequest(BaseModel):
    pin: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=6, max_length=8)
    ]
    device_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not v.isdigit():
            raise PydanticCustomError(
                "pin_not_numeric",
                "PIN must contain only numbers",
            )
        return v


class PINStatusResponse(BaseModel):
    has_pin: bool
    device_id: Optional[str] = None
    pin_created_at: Optional[str] = None


class PINRemoveRequest(BaseModel):
    device_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
