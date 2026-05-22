from __future__ import annotations

from typing import Any


from fastapi import APIRouter, Depends, Query
from urllib.parse import unquote

# from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date

from app import models, schemas
from app.api.dependencies import get_current_user, require_admin
from app.database import get_db
from app.services import users as users_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=schemas.UserOut)
def get_my_profile(current_user: models.User = Depends(get_current_user)):
    return users_service.get_my_profile(current_user)


@router.patch("/me", response_model=schemas.UserOut)
def update_my_profile(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Any:
    return users_service.update_my_profile(payload, db, current_user)


@router.get("", response_model=schemas.PaginatedAdminUsersResponse)
def list_users_admin(
	db: Session = Depends(get_db),
	admin_user: models.User = Depends(require_admin),
	page: int = Query(1, ge=1),
	limit: int = Query(10, ge=1, le=100),
	search: str | None = Query(None),
):
	return users_service.list_users_admin(db, page, limit, search)

@router.get("/metrics")
def get_user_metrics(
    db: Session = Depends(get_db),
    start_date: date = Query(..., alias="from"),
    end_date: date = Query(..., alias="to"),
):
    return users_service.get_user_metrics(db, start_date, end_date)

@router.post("/me/upload-url")
def generate_upload_url(
    content_type: str,
    current_user: models.User = Depends(get_current_user),
):
	return users_service.generate_upload_url(content_type, current_user)

@router.get("/{id}", response_model=schemas.UserPublicOut)
def get_user_public_profile_by_id(id: int, db: Session = Depends(get_db)):
    return users_service.get_user_public_profile_by_id(id, db)