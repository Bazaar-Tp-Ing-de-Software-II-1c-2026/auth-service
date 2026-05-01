from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from loguru import logger

from app import schemas
from app.api.dependencies import get_current_user, get_db
from app.services import pin_service

router = APIRouter(prefix="/api/pin", tags=["PIN Authentication"])


@router.post("/setup", response_model=dict)
def setup_pin(
    payload: schemas.PINSetupRequest,
    current_user: schemas.UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Configure PIN authentication for the current user on a specific device.
    
    **CA 1: Configuración del PIN**
    - Requires authentication
    - PIN must be 6-8 digits
    - Associates PIN with device_id
    """
    logger.info(f"[PIN API] Setup PIN request from user_id={current_user.id}")
    return pin_service.setup_pin(current_user.id, payload, db)


@router.post("/login", response_model=schemas.Token)
def login_with_pin(
    payload: schemas.PINLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate using PIN (device-specific).
    
    **CA 2: Autenticación con PIN**
    - No authentication required (this IS the authentication)
    - Validates PIN and device_id
    - Returns JWT token on success
    
    **CA 3: PIN incorrecto**
    - Tracks failed attempts
    - Locks after 5 failed attempts for 30 minutes
    
    **CA 4: PIN ligado al dispositivo**
    - Only works on the device where PIN was configured
    """
    logger.info(f"[PIN API] PIN login attempt for device_id={payload.device_id}")
    return pin_service.login_with_pin(payload, db)


@router.get("/status", response_model=schemas.PINStatusResponse)
def get_pin_status(
    current_user: schemas.UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get PIN configuration status for the current user.
    
    Returns whether user has PIN configured and on which device.
    """
    logger.info(f"[PIN API] Get PIN status for user_id={current_user.id}")
    return pin_service.get_pin_status(current_user.id, db)


@router.delete("/remove", response_model=dict)
def remove_pin(
    payload: schemas.PINRemoveRequest,
    current_user: schemas.UserOut = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove PIN configuration for the current user.
    
    Requires device_id to match for security.
    """
    logger.info(f"[PIN API] Remove PIN request from user_id={current_user.id}")
    return pin_service.remove_pin(current_user.id, payload, db)

# Made with Bob
