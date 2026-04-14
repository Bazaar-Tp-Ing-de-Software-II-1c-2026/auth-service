from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app import models, schemas
from app.config import settings
from app.exceptions.handler import ServiceException
from app.api.dependencies import get_current_user

import boto3

s3 = boto3.client("s3", region_name=settings.AWS_REGION)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=schemas.UserOut)
def get_my_profile(current_user: models.User = Depends(get_current_user)):
    logger.debug(f"[USER ROUTER] GET /me: user_id={current_user.id}")
    return current_user


@router.patch("/me", response_model=schemas.UserOut)
def update_my_profile(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Any:
    logger.debug(f"[USER ROUTER] PATCH /me: user_id={current_user.id}")
    update_data = payload.model_dump(exclude_unset=True, mode="json")

    if "username" in update_data and update_data["username"] != current_user.username:
        if db.query(models.User).filter(models.User.username == update_data["username"]).first():
            raise ServiceException(status_code=400, title="Bad Request", detail="El nombre de usuario ya existe.")

    for key, value in update_data.items():
        setattr(current_user, key, value)

    try:
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        logger.info(f"[USER ROUTER] Perfil actualizado EXITOSAMENTE: user_id={current_user.id}")
        return current_user
    except Exception as e:
        db.rollback()
        logger.error(f"[USER ROUTER] Error actualizando perfil user_id={current_user.id}: {e}")
        raise ServiceException(status_code=500, title="Internal Server Error", detail="Error interno al procesar la actualización del perfil.")


@router.get("/by-username/{username}", response_model=schemas.UserPublicOut)
def get_user_public_profile_by_username(username: str, db: Session = Depends(get_db)):
    logger.debug(f"[USER ROUTER] GET /by-username/{username}")
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="Usuario no encontrado.")

    if user.blocked:
        raise ServiceException(status_code=403, title="Forbidden", detail="Este perfil no está disponible.")

    return user


@router.get("/{id}", response_model=schemas.UserPublicOut)
def get_user_public_profile_by_id(id: int, db: Session = Depends(get_db)):
    logger.debug(f"[USER ROUTER] GET /{id}")
    user = db.query(models.User).filter(models.User.id == id).first()

    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="Usuario no encontrado.")

    if user.blocked:
        raise ServiceException(status_code=403, title="Forbidden", detail="Este perfil no está disponible.")

    return user


@router.post("/me/upload-url")
def generate_upload_url(
    content_type: str,
    current_user: models.User = Depends(get_current_user),
):
    logger.debug(f"[USER ROUTER] Generando upload URL: user_id={current_user.id}, content_type={content_type}")

    if not content_type.startswith("image/"):
        raise ServiceException(status_code=400, title="Bad Request", detail="Tipo de contenido inválido. Solo se aceptan imágenes.")

    if not settings.S3_BUCKET_NAME:
        logger.error("[USER ROUTER] S3_BUCKET_NAME no está configurado")
        raise ServiceException(status_code=500, title="Internal Server Error", detail="Configuración de S3 incompleta.")

    ext = content_type.split("/")[-1]
    filename = f"users/{current_user.id}/avatar.{ext}"

    try:
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
        raise ServiceException(status_code=500, title="Internal Server Error", detail=f"Error generando URL presignada: {e}")