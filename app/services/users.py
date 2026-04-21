from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from loguru import logger
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.exceptions.handler import ServiceException
from app.repositories import users as users_repository
from app.services.storage import get_s3_client


def get_my_profile(current_user: models.User) -> models.User:
    logger.debug(f"[USER ROUTER] GET /me: user_id={current_user.id}")
    return current_user


def update_my_profile(
    payload: schemas.UserUpdate,
    db: Session,
    current_user: models.User,
) -> Any:
    logger.debug(f"[USER ROUTER] PATCH /me: user_id={current_user.id}")
    update_data = payload.model_dump(mode="json")
    logger.debug(f"[USER ROUTER] Datos a actualizar: {update_data}")

    for key, value in update_data.items():
        logger.debug(f"[USER ROUTER] Actualizando campo: {key}={value}")
        setattr(current_user, key, value)

    try:
        users_repository.save_user(db, current_user)
        logger.info(f"[USER ROUTER] Perfil actualizado EXITOSAMENTE: user_id={current_user.id}")
        return current_user
    except Exception as e:
        db.rollback()
        logger.error(f"[USER ROUTER] Error actualizando perfil user_id={current_user.id}: {e}")
        raise ServiceException(status_code=500, title="Internal Server Error", detail="Internal error while processing profile update.")


def get_user_public_profile_by_username(username: str, db: Session):
    logger.debug(f"[USER ROUTER] GET /by-username/{username}")
    user = users_repository.get_user_by_username(db, username)

    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="User not found.")

    if user.blocked:
        raise ServiceException(status_code=403, title="Forbidden", detail="This profile is not available.")

    return user


def get_user_public_profile_by_id(user_id: int, db: Session):
    logger.debug(f"[USER ROUTER] GET /{user_id}")
    user = users_repository.get_user_by_id(db, user_id)

    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="User not found.")

    if user.blocked:
        raise ServiceException(status_code=403, title="Forbidden", detail="This profile is not available.")

    return user


def generate_upload_url(content_type: str, current_user: models.User):
    logger.debug(f"[USER ROUTER] Generando upload URL: user_id={current_user.id}, content_type={content_type}")

    content_type = unquote(content_type)
    if not content_type.startswith("image/"):
        raise ServiceException(status_code=400, title="Bad Request", detail="Invalid content type. Only images are accepted.")

    if not settings.S3_BUCKET_NAME:
        logger.error("[USER ROUTER] S3_BUCKET_NAME no está configurado")
        raise ServiceException(status_code=500, title="Internal Server Error", detail="Incomplete S3 configuration.")

    ext = content_type.split("/")[-1]
    filename = f"users/{current_user.id}/avatar.{ext}"

    try:
        s3 = get_s3_client()
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": filename, "ContentType": content_type},
            ExpiresIn=300,
        )
        file_url = f"https://{settings.S3_BUCKET_NAME}.s3.amazonaws.com/{filename}"
        logger.info(f"[USER ROUTER] Upload URL generada EXITOSAMENTE: user_id={current_user.id}, key={filename}")
        return {"upload_url": upload_url, "file_url": file_url}

    except Exception as e:
        logger.error(f"[USER ROUTER] Error generando upload URL: user_id={current_user.id}, error={e}")
        raise ServiceException(status_code=500, title="Internal Server Error", detail=f"Error generating presigned URL: {e}")
