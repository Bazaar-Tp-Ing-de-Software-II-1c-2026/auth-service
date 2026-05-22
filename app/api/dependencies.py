from fastapi import Header, Depends
from sqlalchemy.orm import Session
from loguru import logger
from typing import Optional

from app.database import get_db
from app import models, security
from app.exceptions.handler import ServiceException


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:

    if not authorization or not authorization.lower().startswith("bearer "):
        raise ServiceException(
            status_code=401, title="Unauthorized", detail="Missing token"
        )

    token = authorization.split()[1]
    data = security.decode_token(token)

    if not data:
        raise ServiceException(
            status_code=401, title="Unauthorized", detail="Invalid token"
        )

    user_id = data.get("sub")
    if user_id is None:
        raise ServiceException(
            status_code=401,
            title="Unauthorized",
            detail="Invalid token: missing user id",
        )

    user = db.get(models.User, int(user_id))
    if not user:
        raise ServiceException(
            status_code=404, title="Not Found", detail="User not found"
        )

    return user


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        token = authorization.split()[1]
        data = security.decode_token(token)
        if not data:
            return None
        user_id = data.get("sub")
        if user_id is None:
            return None
        return db.get(models.User, int(user_id))
    except Exception:
        return None


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != "admin":
        raise ServiceException(status_code=403, title="Forbidden", detail="Admin only")
    return current_user
