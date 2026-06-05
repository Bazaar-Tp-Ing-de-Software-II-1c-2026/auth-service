from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import datetime


class AddressBase(BaseModel):
    name: str
    address: str
    city: str
    state: str
    postal_code: str
    country: str
    phone: Optional[str] = None
    is_default: bool = False

    @field_validator("name", "address", "city", "state", "country")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("This field cannot be empty")
        if len(v) > 200:
            raise ValueError("Field is too long")
        return v.strip()

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Postal code cannot be empty")
        if len(v) > 20:
            raise ValueError("Postal code is too long")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 20:
            raise ValueError("Phone number is too long")
        return v


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    is_default: Optional[bool] = None


class AddressOut(AddressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AddressListResponse(BaseModel):
    data: list[AddressOut]
    total: int
