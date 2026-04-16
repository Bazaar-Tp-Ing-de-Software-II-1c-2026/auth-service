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
            detail=f"Debes esperar antes de {context}. Intenta en {wait} segundos.",
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
        raise ServiceException(status_code=400, title="Bad Request", detail="El correo electrónico ya está registrado.")

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
            detail="Usuario no encontrado. Si no tenés cuenta, registrate primero.",
        )

    if user.blocked:
        raise ServiceException(status_code=403, title="Forbidden", detail="Tu cuenta ha sido bloqueada.")

    if not user.is_verified:
        raise ServiceException(status_code=403, title="Forbidden", detail="Verificá tu email antes de iniciar sesión.")

    if not security.verify_password(payload.password, user.hashed_password):
        raise ServiceException(status_code=401, title="Unauthorized", detail="Usuario o contraseña incorrectos.")

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
        raise ServiceException(status_code=401, title="Unauthorized", detail="Token de Google inválido o expirado.")

    email = idinfo.get("email")
    if not email:
        raise ServiceException(status_code=400, title="Bad Request", detail="Email no encontrado en el token de Google.")

    first_name = idinfo.get("given_name", "")
    last_name = idinfo.get("family_name", "")

    user = auth_repository.get_user_by_email(db, email)

    if user:
        if user.blocked:
            raise ServiceException(status_code=403, title="Forbidden", detail="Tu cuenta ha sido bloqueada.")

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
        raise ServiceException(status_code=401, title="Unauthorized", detail="Token de verificación inválido o expirado.")

    user_id = data.get("sub")
    if user_id is None:
        raise ServiceException(status_code=401, title="Unauthorized", detail="Token de verificación inválido.")

    user = auth_repository.get_user_by_id(db, int(user_id))
    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="Usuario no encontrado.")

    if user.is_verified:
        return {"message": "El correo ya está verificado."}

    user.is_verified = True
    auth_repository.save(db, user)
    _send_welcome_email_safe(user)

    logger.info(f"[AUTH ROUTER] Email verificado EXITOSAMENTE: user_id={user.id}")
    return {"message": "Email verificado exitosamente. Ya podés iniciar sesión."}


def resend_verification_email(payload: schemas.ResendVerificationEmailRequest, db: Session):
    logger.debug(f"[AUTH ROUTER] Solicitud de reenvío de verificación: email={payload.email}")
    user = auth_repository.get_user_by_email(db, payload.email)

    if user and not user.is_verified:
        _check_rate_limit(user.last_verification_email_request, "solicitar otro código")
        user.last_verification_email_request = datetime.now(timezone.utc)
        _send_verification_email(user, db)
        logger.info(f"[AUTH ROUTER] Email de verificación reenviado: user_id={user.id}")

    return {"message": "Si existe una cuenta con ese email y no está verificada, se envió un nuevo código."}


def verify_code(payload: schemas.VerifyCodeRequest, db: Session):
    logger.debug(f"[AUTH ROUTER] Verificación de código: email={payload.email}")
    user = auth_repository.get_user_by_email(db, payload.email)

    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="Usuario no encontrado.")

    if user.is_verified:
        return {"message": "El correo ya está verificado. Podés iniciar sesión."}

    if not user.verification_code:
        raise ServiceException(status_code=400, title="Bad Request", detail="No hay código de verificación enviado para esta cuenta.")

    if user.verification_code_expires and user.verification_code_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ServiceException(status_code=400, title="Bad Request", detail="El código ha expirado. Solicitá uno nuevo.")

    if user.verification_code.lower() != payload.code.lower():
        raise ServiceException(status_code=400, title="Bad Request", detail="El código es incorrecto.")

    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    auth_repository.save(db, user)
    _send_welcome_email_safe(user)

    logger.info(f"[AUTH ROUTER] Código verificado EXITOSAMENTE: user_id={user.id}")
    return {"message": "Correo verificado exitosamente. Ya podés iniciar sesión."}


def request_reset_password(payload: schemas.ForgotPasswordRequest, db: Session):
    logger.debug(f"[AUTH ROUTER] Solicitud de reset de contraseña: email={payload.email}")
    user = auth_repository.get_user_by_email(db, payload.email)

    if user:
        _check_rate_limit(user.last_password_reset_request, "solicitar otro reset")

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

    return {"message": "Si existe una cuenta con ese email, se envió un email de reset de contraseña."}


def reset_password_with_code(payload: schemas.ResetPasswordWithCodeRequest, db: Session):
    logger.debug(f"[AUTH ROUTER] Reset de contraseña con código: email={payload.email}")
    user = auth_repository.get_user_by_email(db, payload.email)

    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="Usuario no encontrado.")

    if not user.verification_code:
        raise ServiceException(status_code=400, title="Bad Request", detail="No hay código de reseteo enviado para esta cuenta.")

    if user.verification_code_expires and user.verification_code_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ServiceException(status_code=400, title="Bad Request", detail="El código ha expirado. Solicitá uno nuevo.")

    if user.verification_code.lower() != payload.code.lower():
        raise ServiceException(status_code=400, title="Bad Request", detail="El código es incorrecto.")

    user.hashed_password = security.hash_password(payload.new_password)
    user.verification_code = None
    user.verification_code_expires = None
    auth_repository.save(db, user)

    logger.info(f"[AUTH ROUTER] Contraseña reseteada EXITOSAMENTE: user_id={user.id}")
    return {"message": "Contraseña actualizada exitosamente. Ya podés iniciar sesión con tu nueva contraseña."}


def reset_password(payload: schemas.ResetPassword, db: Session):
    logger.debug("[AUTH ROUTER] Reset de contraseña por token")
    data = security.decode_token(payload.token)

    if not data or data.get("scope") != "password-reset":
        raise ServiceException(status_code=401, title="Unauthorized", detail="Token de reset inválido o expirado.")

    user_id = data.get("sub")
    if user_id is None:
        raise ServiceException(status_code=401, title="Unauthorized", detail="Token de reset inválido.")

    user = auth_repository.get_user_by_id(db, int(user_id))
    if not user:
        raise ServiceException(status_code=404, title="Not Found", detail="Usuario no encontrado.")

    token_expires = user.reset_token_expires
    if (
        user.reset_token != payload.token
        or not token_expires
        or token_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
    ):
        raise ServiceException(status_code=401, title="Unauthorized", detail="El token de reset ha expirado.")

    user.hashed_password = security.hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    auth_repository.save(db, user)

    logger.info(f"[AUTH ROUTER] Contraseña reseteada por token EXITOSAMENTE: user_id={user.id}")
    return {"message": "Contraseña reseteada exitosamente. Ya podés iniciar sesión con tu nueva contraseña."}
