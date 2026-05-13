from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.dependencies import get_current_user
from app.database import get_db
from app.logger import logger

router = APIRouter(prefix="/api/push-tokens", tags=["push-tokens"])


class DeviceTokenRegister(schemas.BaseModel):
    token: str
    device_id: str | None = None
    platform: str | None = None  # android, ios, web
    provider: str = "fcm"


class DeviceTokenResponse(schemas.BaseModel):
    id: int
    user_id: int
    token: str
    device_id: str | None = None
    platform: str | None = None
    provider: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post(
    "/register",
    response_model=DeviceTokenResponse,
    status_code=201,
)
def register_device_token(
    payload: DeviceTokenRegister,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Register or update a device token for the current user.
    """

    logger.info(
        f"[DEVICES] Registering token for user {current_user.id} "
        f"(device: {payload.device_id})"
    )

    # Search by token because FCM tokens are globally unique
    existing = (
        db.query(models.DeviceToken)
        .filter(models.DeviceToken.token == payload.token)
        .first()
    )

    if existing:
        existing.user_id = current_user.id
        existing.device_id = payload.device_id
        existing.platform = payload.platform
        existing.provider = payload.provider
        existing.is_active = True
        existing.last_seen_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(existing)

        logger.info(
            f"[DEVICES] Updated existing token for user {current_user.id}"
        )

        return existing

    device_token = models.DeviceToken(
        user_id=current_user.id,
        token=payload.token,
        device_id=payload.device_id,
        platform=payload.platform,
        provider=payload.provider,
        is_active=True,
        last_seen_at=datetime.now(timezone.utc),
    )

    db.add(device_token)
    db.commit()
    db.refresh(device_token)

    logger.info(
        f"[DEVICES] Created new token for user {current_user.id}"
    )

    return device_token


@router.get(
    "/me",
    response_model=list[DeviceTokenResponse],
)
def get_my_device_tokens(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all active device tokens for the current user.
    """

    tokens = (
        db.query(models.DeviceToken)
        .filter(
            models.DeviceToken.user_id == current_user.id,
            models.DeviceToken.is_active.is_(True),
        )
        .all()
    )

    return tokens


@router.get(
    "/users/{user_id}/tokens",
    response_model=list[str],
)
def get_user_tokens(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Internal endpoint used by notification-service
    to fetch all active tokens for a user.
    """

    tokens = (
        db.query(models.DeviceToken.token)
        .filter(
            models.DeviceToken.user_id == user_id,
            models.DeviceToken.is_active.is_(True),
        )
        .all()
    )

    return [token[0] for token in tokens]


@router.post(
    "/deactivate/{token_id}",
    response_model=dict,
)
def deactivate_token(
    token_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate a device token.
    """

    token = (
        db.query(models.DeviceToken)
        .filter(
            models.DeviceToken.id == token_id,
            models.DeviceToken.user_id == current_user.id,
        )
        .first()
    )

    if not token:
        raise HTTPException(
            status_code=404,
            detail="Token not found",
        )

    token.is_active = False

    db.commit()

    logger.info(
        f"[DEVICES] Deactivated token {token_id} "
        f"for user {current_user.id}"
    )

    return {
        "message": "Token deactivated"
    }