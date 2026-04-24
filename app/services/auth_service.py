from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from loguru import logger
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.config import settings
from app.exceptions.handler import ServiceException
from app.repositories import auth_repository
from app.utils.email import send_reset_password_email, send_verification_email, send_welcome_email
from app.utils.verification import generate_verification_code

_RATE_LIMIT_SECONDS = 60
_PIN_MAX_ATTEMPTS = 5
_PIN_LOCK_MINUTES = 15


def _get_google_userinfo_from_access_token(access_token: str) -> dict | None:
    """Fallback for web OAuth flows that return access_token instead of id_token."""
    try:
        response = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5.0,
        )
    except httpx.HTTPError as e:
        logger.warning(f"[AUTH] Error consultando Google UserInfo: {e}")
        return None

    if response.status_code != 200:
        logger.warning(f"[AUTH] Google UserInfo devolvió status={response.status_code}")
        return None

    return response.json()


def _check_rate_limit(last_request: datetime | None, context: str) -> None:
    """Lanza ServiceException si no pasó suficiente tiempo desde el último intento."""
    if last_request is None:
        return
    elapsed = (datetime.now(timezone.utc) - last_request.replace(tzinfo=timezone.utc)).total_seconds()
    if elapsed < _RATE_LIMIT_SECONDS:
        wait = int(_RATE_LIMIT_SECONDS - elapsed)
        raise ServiceException(
            status_code=429,
            title="Too Many Requests",
            detail=f"Please wait before {context}. Try again in {wait} seconds.",
        )


def _send_verification_email(user: models.User, db: Session) -> None:
    verification_code = generate_verification_code(length=8)
    user.verification_code = verification_code
    user.verification_code_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    auth_repository.save(db, user)
    send_verification_email(
        to_email=user.email,
        username=user.first_name or user.username,
        verification_code=verification_code,
    )
    logger.debug(f"[AUTH] Email de verificación enviado a: {user.email}")


def _send_welcome_email_safe(user: models.User) -> None:
    try:
        send_welcome_email(to_email=user.email, username=user.first_name or user.username)
        logger.info(f"[AUTH] Email de bienvenida enviado a: {user.email}")
    except Exception as e:
        logger.warning(f"[AUTH] Error enviando email de bienvenida a {user.email}: {e}")


def register(payload: schemas.UserCreate, db: Session):
    logger.debug(f"[AUTH ROUTER] Intento de registro: email={payload.email}, username={payload.username}")

    if auth_repository.get_user_by_email(db, payload.email):
        raise ServiceException(status_code=400, title="Bad Request", detail="Email is already registered.")

    user = models.User(
        email=payload.email,
        username=payload.username,
        hashed_password=security.hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role="user",
    )

    try:
        auth_repository.create_user(db, user)
        _send_verification_email(user, db)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(user)
    logger.info(f"[AUTH ROUTER] Usuario registrado EXITOSAMENTE: id={user.id}, email={user.email}")
    return user


def login(payload: schemas.UserLogin, db: Session):
    logger.debug(f"[AUTH ROUTER] Intento de login: identifier={payload.identifier}")

    user = auth_repository.get_user_by_identifier(db, payload.identifier)

    if not user:
        raise ServiceException(
            status_code=404,
            title="Not Found",
            detail="User not found. If you do not have an account, please register first.",
        )

    if user.blocked:
        raise ServiceException(status_code=403, title="Forbidden", detail="Your account has been blocked.")

    if not user.is_verified:
        raise ServiceException(status_code=403, title="Forbidden", detail="Please verify your email before logging in.")

    if not security.verify_password(payload.password, user.hashed_password):
        raise ServiceException(status_code=401, title="Unauthorized", detail="Invalid username or password.")

    token = security.create_access_token({"sub": str(user.id), "email": user.email, "username": user.username})
    logger.info(f"[AUTH ROUTER] Login EXITOSO: id={user.id}, username={user.username}")
    return {"access_token": token, "token_type": "bearer"}


def google_login(payload: schemas.GoogleLoginRequest, db: Session):
    logger.debug("[AUTH ROUTER] Intento de Google login")

    if not settings.GOOGLE_CLIENT_ID_WEB and not settings.GOOGLE_CLIENT_ID_ANDROID:
        raise ServiceException(status_code=500, title="Internal Server Error", detail="Google Client IDs not configured")

    raw_google_token = payload.id_token.strip()
    idinfo = None
    for client_id in filter(None, [settings.GOOGLE_CLIENT_ID_WEB, settings.GOOGLE_CLIENT_ID_ANDROID]):
        try:
            idinfo = id_token.verify_oauth2_token(raw_google_token, google_requests.Request(), client_id)
            break
        except Exception as e:
            logger.warning(f"[AUTH] Fallo verificación Google con client_id={client_id}: {e}")

    # Web flow can send access tokens (prefixed with ya29.) instead of JWT id_tokens.
    if not idinfo and raw_google_token.startswith("ya29."):
        idinfo = _get_google_userinfo_from_access_token(raw_google_token)

    if not idinfo:
        raise ServiceException(status_code=401, title="Unauthorized", detail="Invalid or expired Google token.")

    email = idinfo.get("email")
    if not email:
        raise ServiceException(status_code=400, title="Bad Request", detail="Email not found in Google token.")

    first_name = idinfo.get("given_name", "")
    last_name = idinfo.get("family_name", "")

    user = auth_repository.get_user_by_email(db, email)

    if user:
        if user.blocked:
            raise ServiceException(status_code=403, title="Forbidden", detail="Your account has been blocked.")

        if not user.first_name and first_name:
            user.first_name = first_name
        if not user.last_name and last_name:
            user.last_name = last_name

        if not user.is_verified:
            user.is_verified = True
            _send_welcome_email_safe(user)

    else:
        username_base = email.split("@")[0]
        username = auth_repository.generate_unique_username(db, username_base)

        user = models.User(
            email=email,
            username=username,
            hashed_password=security.hash_password(os.urandom(32).hex()),
            first_name=first_name,
            last_name=last_name,
            role="user",
            is_verified=True,
        )
        auth_repository.create_user(db, user)
        _send_welcome_email_safe(user)

    db.commit()
    db.refresh(user)

    token = security.create_access_token({"sub": str(user.id), "email": user.email, "username": user.username})
    logger.info(f"[AUTH ROUTER] Google login EXITOSO: id={user.id}, email={user.email}")
    return {"access_token": token, "token_type": "bearer"}


def verify_email(token: str, db: Session):
    logger.debug("[AUTH ROUTER] Intento de verificación de email por token")
    data = security.decode_token(token)

    if not data or data.get("scope") != "email-verification":
        raise ServiceException(status_code=401, title="Unauthorized", detail="Invalid or expired verification token.")

    user_id = data.get("sub")
    if user_id is None:
        raise ServiceException(status_code=401, title="Unauthorized", detail="Invalid verification token.")

    user = auth_repository.get_user_by_id(db, int(user_id))
    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="User not found.")

    if user.is_verified:
        return {"message": "The email is already verified. You can now log in."}

    user.is_verified = True
    auth_repository.save(db, user)
    _send_welcome_email_safe(user)

    logger.info(f"[AUTH ROUTER] Email verificado EXITOSAMENTE: user_id={user.id}")
    return {"message": "Email verified successfully. You can now log in."}


def resend_verification_email(payload: schemas.ResendVerificationEmailRequest, db: Session):
    logger.debug(f"[AUTH ROUTER] Solicitud de reenvío de verificación: email={payload.email}")
    user = auth_repository.get_user_by_email(db, payload.email)

    if user and not user.is_verified:
        _check_rate_limit(user.last_verification_email_request, "requesting another verification code")
        user.last_verification_email_request = datetime.now(timezone.utc)
        _send_verification_email(user, db)
        logger.info(f"[AUTH ROUTER] Email de verificación reenviado: user_id={user.id}")

    return {"message": "If an account exists with that email and is not verified, a new code has been sent."}


def verify_code(payload: schemas.VerifyCodeRequest, db: Session):
    logger.debug(f"[AUTH ROUTER] Verificación de código: email={payload.email}")
    user = auth_repository.get_user_by_email(db, payload.email)

    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="User not found.")

    if user.is_verified:
        return {"message": "The email is already verified. You can now log in."}

    if not user.verification_code:
        raise ServiceException(status_code=400, title="Bad Request", detail="No verification code has been sent for this account.")

    if user.verification_code_expires and user.verification_code_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ServiceException(status_code=400, title="Bad Request", detail="Code has expired. Please request a new one.")

    if user.verification_code.lower() != payload.code.lower():
        raise ServiceException(status_code=400, title="Bad Request", detail="Incorrect code.")

    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    auth_repository.save(db, user)
    _send_welcome_email_safe(user)

    logger.info(f"[AUTH ROUTER] Código verificado EXITOSAMENTE: user_id={user.id}")
    return {"message": "Email verified successfully. You can now log in."}


def request_reset_password(payload: schemas.ForgotPasswordRequest, db: Session):
    logger.debug(f"[AUTH ROUTER] Solicitud de reset de contraseña: email={payload.email}")
    user = auth_repository.get_user_by_email(db, payload.email)

    if user:
        _check_rate_limit(user.last_password_reset_request, "requesting another password reset")

        reset_code = generate_verification_code(length=8)
        user.verification_code = reset_code
        user.verification_code_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        user.last_password_reset_request = datetime.now(timezone.utc)
        auth_repository.save(db, user)

        send_reset_password_email(
            to_email=user.email,
            username=user.first_name or user.username,
            reset_code=reset_code,
        )
        logger.info(f"[AUTH ROUTER] Email de reset enviado: user_id={user.id}")

    return {"message": "If an account exists with that email, a password reset email has been sent."}


def reset_password_with_code(payload: schemas.ResetPasswordWithCodeRequest, db: Session):
    logger.debug(f"[AUTH ROUTER] Reset de contraseña con código: email={payload.email}")
    user = auth_repository.get_user_by_email(db, payload.email)

    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="User not found.")

    if not user.verification_code:
        raise ServiceException(status_code=400, title="Bad Request", detail="No password reset code has been sent for this account.")

    if user.verification_code_expires and user.verification_code_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ServiceException(status_code=400, title="Bad Request", detail="Code has expired. Please request a new one.")

    if user.verification_code.lower() != payload.code.lower():
        raise ServiceException(status_code=400, title="Bad Request", detail="Incorrect code.")

    user.hashed_password = security.hash_password(payload.new_password)
    user.verification_code = None
    user.verification_code_expires = None
    auth_repository.save(db, user)

    logger.info(f"[AUTH ROUTER] Contraseña reseteada EXITOSAMENTE: user_id={user.id}")
    return {"message": "Password successfully updated. You can now log in with your new password."}


def reset_password(payload: schemas.ResetPassword, db: Session):
    logger.debug("[AUTH ROUTER] Reset de contraseña por token")
    data = security.decode_token(payload.token)

    if not data or data.get("scope") != "password-reset":
        raise ServiceException(status_code=401, title="Unauthorized", detail="Invalid or expired reset token.")

    user_id = data.get("sub")
    if user_id is None:
        raise ServiceException(status_code=401, title="Unauthorized", detail="Invalid reset token.")

    user = auth_repository.get_user_by_id(db, int(user_id))
    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="User not found.")

    token_expires = user.reset_token_expires
    if (
        user.reset_token != payload.token
        or not token_expires
        or token_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
    ):
        raise ServiceException(status_code=401, title="Unauthorized", detail="Password reset token has expired.")

    user.hashed_password = security.hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    auth_repository.save(db, user)

    logger.info(f"[AUTH ROUTER] Contraseña reseteada por token EXITOSAMENTE: user_id={user.id}")
    return {"message": "Password reset successfully. You can now log in with your new password."}


def register_pin(payload: schemas.PinRegisterRequest, current_user: models.User, db: Session):
    if current_user.blocked:
        raise ServiceException(status_code=403, title="Forbidden", detail="Your account has been blocked.")

    pin_device = auth_repository.get_pin_device_for_user(db, current_user.id, payload.device_id)
    hashed_pin = security.hash_password(payload.pin)

    if pin_device:
        pin_device.hashed_pin = hashed_pin
        pin_device.pin_length = len(payload.pin)
        pin_device.pin_enabled = True
        pin_device.failed_attempts = 0
        pin_device.locked_until = None
        pin_device.revoked_at = None
        auth_repository.save(db, pin_device)
        logger.info(f"[AUTH ROUTER] PIN actualizado: user_id={current_user.id}, device_id={payload.device_id}")
        return {"message": "PIN registered successfully", "device_id": payload.device_id, "pin_enabled": True}

    existing_device = auth_repository.get_pin_device_by_device_id(db, payload.device_id)
    if existing_device and existing_device.user_id != current_user.id:
        raise ServiceException(
            status_code=409,
            title="Conflict",
            detail="Device is already registered with another account.",
        )

    new_pin_device = models.UserPinDevice(
        user_id=current_user.id,
        device_id=payload.device_id,
        hashed_pin=hashed_pin,
        pin_length=len(payload.pin),
        pin_enabled=True,
        failed_attempts=0,
    )
    auth_repository.create_pin_device(db, new_pin_device)
    logger.info(f"[AUTH ROUTER] PIN registrado: user_id={current_user.id}, device_id={payload.device_id}")
    return {"message": "PIN registered successfully", "device_id": payload.device_id, "pin_enabled": True}


def login_with_pin(payload: schemas.PinLoginRequest, db: Session):
    pin_device = auth_repository.get_pin_device_by_device_id(db, payload.device_id)
    if not pin_device or pin_device.revoked_at is not None or not pin_device.pin_enabled:
        raise ServiceException(status_code=404, title="Not Found", detail="PIN is not configured for this device.")

    now = datetime.now(timezone.utc)
    if pin_device.locked_until and pin_device.locked_until.replace(tzinfo=timezone.utc) > now:
        raise ServiceException(
            status_code=423,
            title="Locked",
            detail="PIN login is temporarily blocked. Please use email and password.",
        )

    user = auth_repository.get_user_by_id(db, pin_device.user_id)
    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="User not found.")

    if user.blocked:
        raise ServiceException(status_code=403, title="Forbidden", detail="Your account has been blocked.")

    if not user.is_verified:
        raise ServiceException(status_code=403, title="Forbidden", detail="Please verify your email before logging in.")

    if not security.verify_password(payload.pin, pin_device.hashed_pin):
        pin_device.failed_attempts = (pin_device.failed_attempts or 0) + 1

        if pin_device.failed_attempts >= _PIN_MAX_ATTEMPTS:
            pin_device.locked_until = datetime.now(timezone.utc) + timedelta(minutes=_PIN_LOCK_MINUTES)
            auth_repository.save(db, pin_device)
            raise ServiceException(
                status_code=423,
                title="Locked",
                detail="PIN login is temporarily blocked. Please use email and password.",
            )

        auth_repository.save(db, pin_device)
        remaining = _PIN_MAX_ATTEMPTS - pin_device.failed_attempts
        raise ServiceException(
            status_code=401,
            title="Unauthorized",
            detail=f"Invalid PIN. Remaining attempts: {remaining}.",
        )

    pin_device.failed_attempts = 0
    pin_device.locked_until = None
    pin_device.last_used_at = datetime.utcnow()
    auth_repository.save(db, pin_device)

    token = security.create_access_token({"sub": str(user.id), "email": user.email, "username": user.username})
    logger.info(f"[AUTH ROUTER] Login PIN EXITOSO: user_id={user.id}, device_id={payload.device_id}")
    return {"access_token": token, "token_type": "bearer"}


def get_pin_status(device_id: str, current_user: models.User, db: Session):
    pin_device = auth_repository.get_pin_device_for_user(db, current_user.id, device_id)
    if not pin_device:
        raise ServiceException(status_code=404, title="Not Found", detail="PIN configuration not found for this device.")

    now = datetime.now(timezone.utc)
    locked = bool(pin_device.locked_until and pin_device.locked_until.replace(tzinfo=timezone.utc) > now)
    remaining_attempts = 0 if locked else max(0, _PIN_MAX_ATTEMPTS - (pin_device.failed_attempts or 0))

    return {
        "device_id": pin_device.device_id,
        "pin_enabled": pin_device.pin_enabled,
        "locked": locked,
        "locked_until": pin_device.locked_until,
        "remaining_attempts": remaining_attempts,
    }


def disable_pin(payload: schemas.PinDisableRequest, current_user: models.User, db: Session):
    pin_device = auth_repository.get_pin_device_for_user(db, current_user.id, payload.device_id)
    if not pin_device:
        raise ServiceException(status_code=404, title="Not Found", detail="PIN configuration not found for this device.")

    pin_device.pin_enabled = False
    pin_device.revoked_at = datetime.utcnow()
    pin_device.failed_attempts = 0
    pin_device.locked_until = None
    auth_repository.save(db, pin_device)
    logger.info(f"[AUTH ROUTER] PIN desactivado: user_id={current_user.id}, device_id={payload.device_id}")
    return {"message": "PIN disabled successfully", "device_id": payload.device_id, "pin_enabled": False}
