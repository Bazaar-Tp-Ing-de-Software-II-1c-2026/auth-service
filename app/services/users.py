from __future__ import annotations

from typing import Any
from urllib.parse import unquote
from datetime import date

import httpx
from loguru import logger
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.exceptions.handler import ServiceException
from app.repositories import users as users_repository
from app.services.storage import get_s3_client
from app.repositories.users import (
    count_total_users,
    get_users_timeline,
    get_users_paginated,
)


def _notify_product_service_block(user_id: int) -> None:
    url = f"{settings.PRODUCT_SERVICE_URL}/internal-products/sellers/{user_id}/block"
    response = httpx.patch(url, timeout=5.0)
    if response.status_code >= 400:
        raise ServiceException(
            status_code=502,
            title="Bad Gateway",
            detail="Failed to notify product-service about user block.",
        )


def _notify_product_service_unblock(user_id: int) -> None:
    url = f"{settings.PRODUCT_SERVICE_URL}/internal-products/sellers/{user_id}/unblock"
    response = httpx.patch(url, timeout=5.0)
    if response.status_code >= 400:
        raise ServiceException(
            status_code=502,
            title="Bad Gateway",
            detail="Failed to notify product-service about user unblock.",
        )


def get_my_profile(current_user: models.User) -> models.User:
    logger.debug(f"[USER ROUTER] GET /me: user_id={current_user.id}")
    return current_user


def update_my_profile(
    payload: schemas.UserUpdate,
    db: Session,
    current_user: models.User,
) -> Any:
    logger.debug(f"[USER ROUTER] PATCH /me: user_id={current_user.id}")
    update_data = payload.model_dump(mode="json", exclude_unset=True)
    logger.debug(f"[USER ROUTER] Datos a actualizar: {update_data}")

    for key, value in update_data.items():
        logger.debug(f"[USER ROUTER] Actualizando campo: {key}={value}")
        setattr(current_user, key, value)

    try:
        users_repository.save_user(db, current_user)
        logger.info(
            f"[USER ROUTER] Perfil actualizado EXITOSAMENTE: user_id={current_user.id}"
        )
        return current_user
    except Exception as e:
        db.rollback()
        logger.error(
            f"[USER ROUTER] Error actualizando perfil user_id={current_user.id}: {e}"
        )
        raise ServiceException(
            status_code=500,
            title="Internal Server Error",
            detail="Internal error while processing profile update.",
        )


def get_user_public_profile_by_username(username: str, db: Session):
    logger.debug(f"[USER ROUTER] GET /by-username/{username}")
    user = users_repository.get_user_by_username(db, username)

    if not user:
        raise ServiceException(
            status_code=404, title="Not Found", detail="User not found."
        )

    if user.blocked:
        raise ServiceException(
            status_code=403, title="Forbidden", detail="This profile is not available."
        )

    return user


def get_user_public_profile_by_id(user_id: int, db: Session):
    logger.debug(f"[USER ROUTER] GET /{user_id}")
    user = users_repository.get_user_by_id(db, user_id)

    if not user:
        raise ServiceException(
            status_code=404, title="Not Found", detail="User not found."
        )

    if user.blocked:
        raise ServiceException(
            status_code=403, title="Forbidden", detail="This profile is not available."
        )

    return user


def generate_upload_url(content_type: str, current_user: models.User):
    logger.debug(
        f"[USER ROUTER] Generando upload URL: user_id={current_user.id}, content_type={content_type}"
    )

    content_type = unquote(content_type)
    if not content_type.startswith("image/"):
        raise ServiceException(
            status_code=400,
            title="Bad Request",
            detail="Invalid content type. Only images are accepted.",
        )

    if not settings.S3_BUCKET_NAME:
        logger.error("[USER ROUTER] S3_BUCKET_NAME no está configurado")
        raise ServiceException(
            status_code=500,
            title="Internal Server Error",
            detail="Incomplete S3 configuration.",
        )

    ext = content_type.split("/")[-1]
    filename = f"users/{current_user.id}/avatar.{ext}"

    try:
        s3 = get_s3_client()
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": filename,
                "ContentType": content_type,
            },
            ExpiresIn=300,
        )
        file_url = f"https://{settings.S3_BUCKET_NAME}.s3.amazonaws.com/{filename}"
        logger.info(
            f"[USER ROUTER] Upload URL generada EXITOSAMENTE: user_id={current_user.id}, key={filename}"
        )
        return {"upload_url": upload_url, "file_url": file_url}

    except Exception as e:
        logger.error(
            f"[USER ROUTER] Error generando upload URL: user_id={current_user.id}, error={e}"
        )
        raise ServiceException(
            status_code=500,
            title="Internal Server Error",
            detail=f"Error generating presigned URL: {e}",
        )


def get_user_metrics(db: Session, start_date: date, end_date: date):
    try:
        total_users = count_total_users(db)
        timeline = get_users_timeline(db, start_date, end_date)

        users_in_period = 0
        formatted_timeline = []

        # Usamos unpacking (row_date, row_count) para evitar el conflicto con tuple.count()
        for row_date, row_count in timeline:
            users_in_period += row_count
            formatted_timeline.append({"date": str(row_date), "count": row_count})

        logger.info(
            f"[USER METRICS] Métricas obtenidas: total_users={total_users}, users_in_period={users_in_period}, timeline_count={len(formatted_timeline)}"
        )

        return {
            "totalUsers": total_users,
            "usersInPeriod": users_in_period,
            "timeline": formatted_timeline,
        }
    except Exception as e:
        logger.error(
            f"[USER METRICS] Error obteniendo métricas: start_date={start_date}, end_date={end_date}, error={e}"
        )
        raise ServiceException(
            status_code=500,
            title="Internal Server Error",
            detail=f"Error fetching user metrics: {str(e)}",
        )


def list_users_admin(
    db: Session,
    page: int,
    limit: int,
    search: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    users, total = get_users_paginated(db, page, limit, search, start_date, end_date)

    data = []
    for user in users:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        data.append(
            {
                "id": user.id,
                "name": full_name or user.username,
                "email": user.email,
                "created_at": user.created_at,
                "status": "blocked" if user.blocked else "active",
                "profile_picture_url": user.profile_picture_url,
            }
        )

    return {
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
    }


def block_user(db: Session, user_id: int, admin_user: models.User):
    logger.debug(f"[USER ROUTER] Admin {admin_user.id} requests block user {user_id}")

    if admin_user.id == user_id:
        raise ServiceException(
            status_code=400,
            title="Bad Request",
            detail="Administrators cannot block their own account.",
        )

    user = users_repository.get_user_by_id(db, user_id)
    if not user:
        raise ServiceException(
            status_code=404, title="Not Found", detail="User not found."
        )

    if user.blocked:
        return {"message": "User is already blocked."}

    user.blocked = True
    try:
        users_repository.save_user(db, user)
    except Exception as e:
        db.rollback()
        logger.error(f"[USER ROUTER] Error bloqueando usuario user_id={user_id}: {e}")
        raise ServiceException(
            status_code=500,
            title="Internal Server Error",
            detail="Error blocking user.",
        )

    try:
        _notify_product_service_block(user.id)
    except Exception as e:
        user.blocked = False
        users_repository.save_user(db, user)
        logger.error(
            f"[USER ROUTER] Error notificando bloqueo a product-service user_id={user_id}: {e}"
        )
        if isinstance(e, ServiceException):
            raise e
        raise ServiceException(
            status_code=502,
            title="Bad Gateway",
            detail="Failed to notify product-service about user block.",
        )

    logger.info(
        f"[USER ROUTER] Usuario bloqueado: user_id={user.id} by admin_id={admin_user.id}"
    )
    return {"message": "User blocked successfully."}


def unblock_user(db: Session, user_id: int, admin_user: models.User):
    logger.debug(f"[USER ROUTER] Admin {admin_user.id} requests unblock user {user_id}")

    user = users_repository.get_user_by_id(db, user_id)
    if not user:
        raise ServiceException(
            status_code=404, title="Not Found", detail="User not found."
        )

    if not user.blocked:
        return {"message": "User is not blocked."}

    user.blocked = False
    try:
        users_repository.save_user(db, user)
    except Exception as e:
        db.rollback()
        logger.error(
            f"[USER ROUTER] Error desbloqueando usuario user_id={user_id}: {e}"
        )
        raise ServiceException(
            status_code=500,
            title="Internal Server Error",
            detail="Error unblocking user.",
        )

    try:
        _notify_product_service_unblock(user.id)
    except Exception as e:
        user.blocked = True
        users_repository.save_user(db, user)
        logger.error(
            f"[USER ROUTER] Error notificando desbloqueo a product-service user_id={user_id}: {e}"
        )
        if isinstance(e, ServiceException):
            raise e
        raise ServiceException(
            status_code=502,
            title="Bad Gateway",
            detail="Failed to notify product-service about user unblock.",
        )

    logger.info(
        f"[USER ROUTER] Usuario desbloqueado: user_id={user.id} by admin_id={admin_user.id}"
    )
    return {"message": "User unblocked successfully."}


def promote_to_admin(
    db: Session,
    user_id: int,
    admin_user: models.User,
):
    logger.debug(
        f"[USER ROUTER] Admin {admin_user.id} promoting user {user_id} to admin"
    )

    if admin_user.id == user_id:
        raise ServiceException(
            status_code=400,
            title="Bad Request",
            detail="You cannot promote yourself.",
        )

    user = users_repository.get_user_by_id(db, user_id)
    if not user:
        raise ServiceException(
            status_code=404,
            title="Not Found",
            detail="User not found.",
        )

    if user.role == "admin":
        return {"message": "User is already admin."}

    user.role = "admin"

    try:
        users_repository.save_user(db, user)
    except Exception as e:
        db.rollback()
        logger.error(f"[USER ROUTER] Error promoting user_id={user_id}: {e}")
        raise ServiceException(
            status_code=500,
            title="Internal Server Error",
            detail="Error promoting user to admin.",
        )

    logger.info(
        f"[USER ROUTER] User promoted to admin: user_id={user.id} by admin_id={admin_user.id}"
    )

    return {"message": "User promoted to admin successfully."}
