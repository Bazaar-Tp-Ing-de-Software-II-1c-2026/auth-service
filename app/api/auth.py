from __future__ import annotations

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.dependencies import get_current_user
from app.database import get_db
from app.services import auth_service
from app.schemas.schemas import (
    UserCreate,
    UserLogin,
    Token,
    UserOut,
    GoogleLoginRequest,
    ResendVerificationEmailRequest,
    VerifyCodeRequest,
    ForgotPasswordRequest,
    ResetPasswordWithCodeRequest,
    ResetPassword,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    return auth_service.register(payload, db)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    return auth_service.login(payload, db)


@router.get("/me", response_model=UserOut)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    logger.debug(f"[AUTH ROUTER] GET /me: user_id={current_user.id}")
    return current_user


@router.post("/google-login", response_model=Token)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    return auth_service.google_login(payload, db)


@router.get("/verify-email", response_model=dict)
def verify_email(token: str, db: Session = Depends(get_db)):
    return auth_service.verify_email(token, db)


@router.post("/resend-verification-email", response_model=dict)
def resend_verification_email(
    payload: ResendVerificationEmailRequest, db: Session = Depends(get_db)
):
    return auth_service.resend_verification_email(payload, db)


@router.post("/verify-code", response_model=dict)
def verify_code(payload: VerifyCodeRequest, db: Session = Depends(get_db)):
    return auth_service.verify_code(payload, db)


@router.post("/request-reset-password", response_model=dict)
def request_reset_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    return auth_service.request_reset_password(payload, db)


@router.post("/reset-password-with-code", response_model=dict)
def reset_password_with_code(
    payload: ResetPasswordWithCodeRequest, db: Session = Depends(get_db)
):
    return auth_service.reset_password_with_code(payload, db)


@router.post("/reset-password", response_model=dict)
def reset_password(payload: ResetPassword, db: Session = Depends(get_db)):
    return auth_service.reset_password(payload, db)
