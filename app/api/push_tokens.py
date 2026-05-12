from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.dependencies import get_current_user
from app.database import get_db
from app.logger import logger

router = APIRouter(prefix="/api/push-tokens", tags=["push-tokens"])


class PushTokenRegister(schemas.BaseModel):
    """Request body for registering a push token."""
    token: str
    device_id: str = None
    platform: str = None  # ios, android, web


class PushTokenResponse(schemas.BaseModel):
    """Response for push token operations."""
    id: int
    user_id: int
    token: str
    is_active: bool


@router.post("/register", response_model=PushTokenResponse, status_code=201)
def register_push_token(
    payload: PushTokenRegister,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register or update a push token for the current user."""
    logger.info(f"[PUSH_TOKENS] Registering token for user {current_user.id} (device: {payload.device_id})")

    # Check if token already exists for this user/device
    existing = (
        db.query(models.PushToken)
        .filter(
            models.PushToken.user_id == current_user.id,
            models.PushToken.device_id == payload.device_id,
        )
        .first()
    )

    if existing:
        # Update existing token
        existing.token = payload.token
        existing.platform = payload.platform
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        logger.info(f"[PUSH_TOKENS] Updated token for user {current_user.id}")
        return existing

    # Create new token
    push_token = models.PushToken(
        user_id=current_user.id,
        token=payload.token,
        device_id=payload.device_id,
        platform=payload.platform,
        is_active=True,
    )
    db.add(push_token)
    db.commit()
    db.refresh(push_token)
    logger.info(f"[PUSH_TOKENS] Created new token for user {current_user.id}")
    return push_token


@router.get("/user-tokens", response_model=list[PushTokenResponse])
def get_user_tokens(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all active push tokens for the current user."""
    tokens = (
        db.query(models.PushToken)
        .filter(
            models.PushToken.user_id == current_user.id,
            models.PushToken.is_active == True,
        )
        .all()
    )
    return tokens


@router.get("/seller/{seller_id}", response_model=list[str])
def get_seller_tokens(
    seller_id: int,
    db: Session = Depends(get_db),
):
    """Get all active push tokens for a seller (for internal use by product-service)."""
    tokens = (
        db.query(models.PushToken.token)
        .filter(
            models.PushToken.user_id == seller_id,
            models.PushToken.is_active == True,
        )
        .all()
    )
    return [token[0] for token in tokens]


@router.post("/deactivate/{token_id}", response_model=dict)
def deactivate_token(
    token_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deactivate a push token."""
    token = (
        db.query(models.PushToken)
        .filter(
            models.PushToken.id == token_id,
            models.PushToken.user_id == current_user.id,
        )
        .first()
    )

    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    token.is_active = False
    db.commit()
    logger.info(f"[PUSH_TOKENS] Deactivated token {token_id} for user {current_user.id}")
    return {"message": "Token deactivated"}
