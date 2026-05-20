from __future__ import annotations

from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.exceptions.handler import ServiceException
from app.repositories import auth_repository

# Constants for PIN security
PIN_MAX_FAILED_ATTEMPTS = 5
PIN_LOCKOUT_MINUTES = 30


def setup_pin(user_id: int, payload: schemas.PINSetupRequest, db: Session) -> dict:
    """
    Configure a PIN for a user on a specific device.

    CA 1: Configuración del PIN
    - User must be authenticated
    - PIN must be at least 6 digits
    - PIN is associated with the device
    """
    logger.debug(
        f"[PIN SERVICE] Setting up PIN for user_id={user_id}, device_id={payload.device_id}"
    )

    user = auth_repository.get_user_by_id(db, user_id)
    if not user:
        raise ServiceException(
            status_code=404, title="Not Found", detail="User not found."
        )

    if user.blocked:
        raise ServiceException(
            status_code=403, title="Forbidden", detail="Your account has been blocked."
        )

    # Hash the PIN using bcrypt (same as password)
    pin_hash = security.hash_password(payload.pin)

    # Store PIN configuration
    user.pin_hash = pin_hash
    user.pin_device_id = payload.device_id
    user.pin_failed_attempts = 0
    user.pin_locked_until = None
    user.pin_created_at = datetime.now(timezone.utc)

    auth_repository.save(db, user)

    logger.info(f"[PIN SERVICE] PIN configured successfully for user_id={user_id}")
    return {
        "message": "PIN configured successfully",
        "device_id": payload.device_id,
        "pin_created_at": user.pin_created_at.isoformat(),
    }


def login_with_pin(payload: schemas.PINLoginRequest, db: Session) -> dict:
    """
    Authenticate a user using their PIN.

    CA 2: Autenticación con PIN
    - User must have PIN configured on this device
    - PIN must match

    CA 3: PIN incorrecto
    - Track failed attempts
    - Lock after max attempts

    CA 4: PIN ligado al dispositivo
    - Verify device_id matches
    """
    logger.debug(f"[PIN SERVICE] PIN login attempt for device_id={payload.device_id}")

    # Find user by device_id
    user = (
        db.query(models.User)
        .filter(models.User.pin_device_id == payload.device_id)
        .first()
    )

    if not user or not user.pin_hash:
        raise ServiceException(
            status_code=401,
            title="Unauthorized",
            detail="PIN authentication not configured for this device. Please sign in with email and password.",
        )

    if user.blocked:
        raise ServiceException(
            status_code=403, title="Forbidden", detail="Your account has been blocked."
        )

    # Check if PIN is locked
    if user.pin_locked_until:
        locked_until = user.pin_locked_until.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        if locked_until > now:
            remaining_minutes = int((locked_until - now).total_seconds() / 60) + 1
            raise ServiceException(
                status_code=403,
                title="Forbidden",
                detail=f"PIN authentication is temporarily locked. Try again in {remaining_minutes} minutes or sign in with email and password.",
            )
        else:
            # Lock expired, reset
            user.pin_locked_until = None
            user.pin_failed_attempts = 0
            auth_repository.save(db, user)

    # Verify PIN
    if not security.verify_password(payload.pin, user.pin_hash):
        # Increment failed attempts
        user.pin_failed_attempts += 1

        if user.pin_failed_attempts >= PIN_MAX_FAILED_ATTEMPTS:
            # Lock the PIN
            user.pin_locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=PIN_LOCKOUT_MINUTES
            )
            auth_repository.save(db, user)

            logger.warning(
                f"[PIN SERVICE] PIN locked for user_id={user.id} after {PIN_MAX_FAILED_ATTEMPTS} failed attempts"
            )
            raise ServiceException(
                status_code=403,
                title="Forbidden",
                detail=f"Too many failed attempts. PIN authentication locked for {PIN_LOCKOUT_MINUTES} minutes. Please sign in with email and password.",
            )

        auth_repository.save(db, user)
        remaining_attempts = PIN_MAX_FAILED_ATTEMPTS - user.pin_failed_attempts

        logger.warning(
            f"[PIN SERVICE] Failed PIN attempt for user_id={user.id}, remaining attempts: {remaining_attempts}"
        )
        raise ServiceException(
            status_code=401,
            title="Unauthorized",
            detail=f"Incorrect PIN. {remaining_attempts} attempts remaining.",
        )

    # PIN is correct, reset failed attempts
    user.pin_failed_attempts = 0
    user.pin_locked_until = None
    auth_repository.save(db, user)

    # Generate JWT token
    token = security.create_access_token(
        {"sub": str(user.id), "email": user.email, "username": user.username}
    )

    logger.info(f"[PIN SERVICE] PIN login successful for user_id={user.id}")
    return {"access_token": token, "token_type": "bearer"}


def get_pin_status(user_id: int, db: Session) -> schemas.PINStatusResponse:
    """
    Get the PIN configuration status for a user.
    """
    logger.debug(f"[PIN SERVICE] Getting PIN status for user_id={user_id}")

    user = auth_repository.get_user_by_id(db, user_id)
    if not user:
        raise ServiceException(
            status_code=404, title="Not Found", detail="User not found."
        )

    has_pin = bool(user.pin_hash and user.pin_device_id)

    return schemas.PINStatusResponse(
        has_pin=has_pin,
        device_id=user.pin_device_id if has_pin else None,
        pin_created_at=user.pin_created_at.isoformat() if user.pin_created_at else None,
    )


def remove_pin(user_id: int, payload: schemas.PINRemoveRequest, db: Session) -> dict:
    """
    Remove PIN configuration for a user.
    """
    logger.debug(
        f"[PIN SERVICE] Removing PIN for user_id={user_id}, device_id={payload.device_id}"
    )

    user = auth_repository.get_user_by_id(db, user_id)
    if not user:
        raise ServiceException(
            status_code=404, title="Not Found", detail="User not found."
        )

    # Verify device_id matches
    if user.pin_device_id != payload.device_id:
        raise ServiceException(
            status_code=403,
            title="Forbidden",
            detail="Device ID does not match. Cannot remove PIN from a different device.",
        )

    # Clear PIN data
    user.pin_hash = None
    user.pin_device_id = None
    user.pin_failed_attempts = 0
    user.pin_locked_until = None
    user.pin_created_at = None

    auth_repository.save(db, user)

    logger.info(f"[PIN SERVICE] PIN removed successfully for user_id={user_id}")
    return {"message": "PIN removed successfully"}
