from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from .auth import get_current_user 

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