from __future__ import annotations

import os
import boto3
import logging
from typing import Any
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from .auth import get_current_user

logger = logging.getLogger(__name__) 

s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION")
)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me", response_model=schemas.UserOut)
def get_my_profile(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=schemas.UserOut)
def update_my_profile(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Any:

    update_data = payload.model_dump(exclude_unset=True, mode="json")

    if "username" in update_data and update_data["username"] != current_user.username:
        user_exists = db.query(models.User).filter(
            models.User.username == update_data["username"]
        ).first()
        
        if user_exists:
            raise HTTPException(
                status_code=400, 
                detail="El nombre de usuario ya existe"
            )

    for key, value in update_data.items():
        setattr(current_user, key, value)

    try:
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        return current_user
        
    except Exception as e:
        db.rollback()
        print(f"Error en update_my_profile: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno al procesar la actualización del perfil"
        )

@router.get("/by-username/{username}", response_model=schemas.UserPublicOut)
def get_user_public_profile_by_username(
    username: str, 
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado"
        )
    
    if user.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este perfil no está disponible"
        )
        
    return user

@router.get("/{username}", response_model=schemas.UserPublicOut)
def get_user_public_profile(
    username: str,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    if user.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este perfil no está disponible"
        )

    return user

@router.get("/{id}", response_model=schemas.UserPublicOut)
def get_user_public_profile_by_id(
    id: int,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado"
        )
    
    if user.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este perfil no está disponible"
        )
        
    return user

@router.post("/me/upload-url")
def generate_upload_url(
    content_type: str,
    current_user: models.User = Depends(get_current_user)
):
    content_type = unquote(content_type)
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Tipo inválido")

    if not BUCKET_NAME:
        logger.error("S3_BUCKET_NAME no está configurado")
        raise HTTPException(
            status_code=500,
            detail="Configuración de S3 incompleta: BUCKET_NAME no definido"
        )

    ext = content_type.split("/")[-1]
    filename = f"users/{current_user.id}/avatar.{ext}"

    try:
        logger.info(f"Generando URL presignada para bucket={BUCKET_NAME}, key={filename}")
        
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": filename,
                "ContentType": content_type
            },
            ExpiresIn=300
        )

        file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"

        logger.info(f"URL presignada generada exitosamente para usuario {current_user.id}")
        return {
            "upload_url": upload_url,
            "file_url": file_url
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error generando URL presignada: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generando URL presignada: {error_msg}"
        )