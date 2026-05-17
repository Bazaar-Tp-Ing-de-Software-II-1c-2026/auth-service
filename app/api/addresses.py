from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..models.address import UserAddress
from ..schemas.address import (
    AddressCreate,
    AddressOut,
    AddressUpdate,
    AddressListResponse,
)
from .dependencies import get_current_user, get_db
from ..models import User

router = APIRouter(prefix="/api/addresses", tags=["addresses"])


@router.get("", response_model=AddressListResponse)
async def get_user_addresses(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get all addresses for the current user"""
    addresses = (
        db.query(UserAddress)
        .filter(UserAddress.user_id == current_user.id)
        .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
        .all()
    )

    return AddressListResponse(data=addresses, total=len(addresses))


@router.post("", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
async def create_address(
    address_data: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new address for the current user"""

    # If this is set as default, remove default from other addresses
    if address_data.is_default:
        db.query(UserAddress).filter(UserAddress.user_id == current_user.id).update(
            {"is_default": False}
        )

    # If this is the first address, make it default automatically
    existing_count = (
        db.query(UserAddress).filter(UserAddress.user_id == current_user.id).count()
    )

    if existing_count == 0:
        address_data.is_default = True

    new_address = UserAddress(**address_data.model_dump(), user_id=current_user.id)

    db.add(new_address)
    db.commit()
    db.refresh(new_address)

    return new_address


@router.get("/{address_id}", response_model=AddressOut)
async def get_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific address"""
    address = (
        db.query(UserAddress)
        .filter(UserAddress.id == address_id, UserAddress.user_id == current_user.id)
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    return address


@router.patch("/{address_id}", response_model=AddressOut)
async def update_address(
    address_id: int,
    address_data: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an address"""
    address = (
        db.query(UserAddress)
        .filter(UserAddress.id == address_id, UserAddress.user_id == current_user.id)
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    # If setting as default, remove default from other addresses
    if address_data.is_default:
        db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id, UserAddress.id != address_id
        ).update({"is_default": False})

    # Update fields
    update_data = address_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(address, field, value)

    db.commit()
    db.refresh(address)

    return address


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an address"""
    address = (
        db.query(UserAddress)
        .filter(UserAddress.id == address_id, UserAddress.user_id == current_user.id)
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    was_default = address.is_default
    db.delete(address)
    db.commit()

    # If deleted address was default, set another as default
    if was_default:
        next_address = (
            db.query(UserAddress).filter(UserAddress.user_id == current_user.id).first()
        )

        if next_address:
            next_address.is_default = True
            db.commit()

    return None


@router.post("/{address_id}/set-default", response_model=AddressOut)
async def set_default_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set an address as the default"""
    address = (
        db.query(UserAddress)
        .filter(UserAddress.id == address_id, UserAddress.user_id == current_user.id)
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    # Remove default from all other addresses
    db.query(UserAddress).filter(UserAddress.user_id == current_user.id).update(
        {"is_default": False}
    )

    # Set this one as default
    address.is_default = True
    db.commit()
    db.refresh(address)

    return address
