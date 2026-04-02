from __future__ import annotations
from datetime import timedelta, datetime
import os
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from ..utils.email import send_email_html
from .. import models
from .. import security
from .. import schemas
from ..models import User
from typing import Optional


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _send_verification_email(user: models.User) -> None:
    token_data = {"sub": str(user.id), "scope": "email-verification"}
    verification_token = security.create_access_token(
        token_data, expires_delta=timedelta(hours=24)
    )
    app_url = os.getenv("APP_PUBLIC_URL", "http://localhost:5173")
    link = f"{app_url}/verify-email?token={verification_token}"

    subject = "Verify your account - Bazaar"
    html_content = f"""
    <html>
        <body>
            <p>Hello {user.first_name},</p>
            <p>Thanks for signing up. Please verify your email to activate your account:</p>
            <a href="{link}" style="background:#0ea5e9;color:#fff;padding:10px;border-radius:5px;">Verify account</a>
            <p>This link expires in 24 hours.</p>
            <p>Best regards,<br/>The Bazaar Team</p>
        </body>
    </html>
    """
    send_email_html(user.email, subject, html_content)


def get_current_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> models.User:
    print(f"[DEBUG] get_current_user: authorization={authorization}")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token faltante")
    token = authorization.split()[1]
    data = security.decode_token(token)
    print(f"[DEBUG] token decoded: {data}")
    if not data:
        raise HTTPException(status_code=401, detail="Token inválido")

    user_id = data.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token inválido (no sub)")

    user = db.query(models.User).get(int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

# Function that gets the user if they are authenticated, otherwise returns None.
def get_optional_user(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> Optional[models.User]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        from ..security import decode_token

        token = authorization.split()[1]
        data = decode_token(token)
        if not data:
            return None
        user_id = data.get("sub")
        if user_id is None:
            return None
        user = db.query(models.User).get(int(user_id))
        return user
    except Exception:
        return None


@router.post("/register", response_model=schemas.UserOut)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(
            status_code=400, detail="El correo electrónico ya está registrado."
        )
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")

    user = models.User(
        email=payload.email,
        username=payload.username,
        hashed_password=security.hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role="user",
    )
    db.add(user)

    try:
        db.flush()
        _send_verification_email(user)

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(
            or_(
                models.User.email == payload.identifier,
                models.User.username == payload.identifier,
            )
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found, if you don't have an account, please register first.",
        )
    
    if user.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    if not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User or password incorrect.",
        )

    token_data = {"sub": str(user.id), "email": user.email, "username": user.username}
    token = security.create_access_token(token_data)

    return {"access_token": token, "token_type": "bearer"}


@router.get("/verify-email", response_model=dict)
def verify_email(token: str, db: Session = Depends(get_db)):
    data = security.decode_token(token)
    if not data or data.get("scope") != "email-verification":
        raise HTTPException(status_code=401, detail="Invalid or expired verification token")

    user_id = data.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid verification token")

    user = db.query(models.User).get(int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        return {"message": "Email is already verified"}

    user.is_verified = True
    db.add(user)
    db.commit()
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification-email", response_model=dict)
def resend_verification_email(
    payload: schemas.ResendVerificationEmailRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user and not user.is_verified:
        _send_verification_email(user)

    return {
        "message": "If an account with that email exists and is not verified, a new verification email has been sent."
    }


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


def _send_reset_password_email(user: models.User, reset_token: str) -> None:
    app_url = os.getenv("APP_PUBLIC_URL", "http://localhost:5173")
    link = f"{app_url}/reset-password?token={reset_token}"

    subject = "Reset your password - Bazaar"
    html_content = f"""
    <html>
        <body>
            <p>Hello {user.first_name},</p>
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            <a href="{link}" style="background:#0ea5e9;color:#fff;padding:10px;border-radius:5px;">Reset Password</a>
            <p>This link expires in 1 hour.</p>
            <p>If you didn't request this, you can ignore this email.</p>
            <p>Best regards,<br/>The Bazaar Team</p>
        </body>
    </html>
    """
    send_email_html(user.email, subject, html_content)


@router.post("/request-reset-password", response_model=dict)
def request_reset_password(
    payload: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    
    if user:
        # Generar token con expiración de 1 hora
        token_data = {"sub": str(user.id), "scope": "password-reset"}
        reset_token = security.create_access_token(
            token_data, expires_delta=timedelta(hours=1)
        )
        
        # Guardar token en BD con expiración
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.add(user)
        db.commit()
        
        # Enviar email
        _send_reset_password_email(user, reset_token)

    # Retornar mensaje genérico por seguridad (no revelar si el email existe)
    return {
        "message": "If an account with that email exists, a password reset email has been sent."
    }


@router.post("/reset-password", response_model=dict)
def reset_password(
    payload: schemas.ResetPassword,
    db: Session = Depends(get_db),
):
    # Validar token
    data = security.decode_token(payload.token)
    if not data or data.get("scope") != "password-reset":
        raise HTTPException(status_code=401, detail="Invalid or expired reset token")

    user_id = data.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid reset token")

    user = db.query(models.User).get(int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar que el token guardado en BD coincida
    if user.reset_token != payload.token or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Reset token has expired")

    # Actualizar contraseña y limpiar token
    user.hashed_password = security.hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.add(user)
    db.commit()

    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.put("/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UserUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.first_name = payload.first_name
    user.last_name = payload.last_name
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/forgot-password", response_model=dict)
def request_password_reset(
    payload: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user: 
        token_data = {"sub": str(user.id), "scope": "password-reset"}
        reset_token = security.create_access_token(token_data, expires_delta=timedelta(hours=1))

        app_url = os.getenv("APP_PUBLIC_URL", "http://localhost:5173")
        link = f"{app_url}/reset-password?token={reset_token}"

        #cuerpo del mail
        subject = "Password Reset Request - Bazaar"
        html_content = f"""
        <html>
            <body>
                <p>Hello {user.first_name},</p>
                <p>We received a request to reset your password. Click the link below to create a new password:</p>
                <a href="{link}" style="background:#0ea5e9;color:#fff;padding:10px;border-radius:5px;">Reset Password</a>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request this change, you can ignore this email.</p>
                <p>Best regards,<br/>The Bazaar Team</p>
            </body>
        </html>
        """

        send_email_html(user.email, subject, html_content)
    return {"message": "If an account with that email/username exists, you will receive an email with instructions to reset your password."}


@router.post("/reset-password-confirmation")
def reset_password_confirmation(
    payload: schemas.ResetPassword, db: Session = Depends(get_db)
):
    data = security.decode_token(payload.token)
    if not data or data.get("scope") != "password-reset":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = data.get("sub")
    user = db.query(models.User).get(int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = security.hash_password(payload.new_password)
    db.add(user)
    db.commit()
    return {"message": "Password has been reset successfully"}


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user