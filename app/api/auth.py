from __future__ import annotations
from datetime import timedelta, datetime
import os
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from ..utils.email import send_email_html, send_verification_email, send_reset_password_email, send_welcome_email
from ..utils.verification import generate_verification_code
from .. import models
from .. import security
from .. import schemas
from ..models import User
from typing import Optional
from google.oauth2 import id_token
from google.auth.transport import requests


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _send_verification_email(user: models.User, db: Session) -> None:
    """Genera un código de verificación aleatorio y lo envía por email"""
    # Generar código aleatorio de 8 caracteres
    verification_code = generate_verification_code(length=8)
    
    # Guardar código y tiempo de expiración en la BD
    user.verification_code = verification_code
    user.verification_code_expires = datetime.utcnow() + timedelta(hours=24)
    db.add(user)
    db.commit()

    send_verification_email(
        to_email=user.email,
        username=user.first_name or user.username,
        verification_code=verification_code
    )


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
        _send_verification_email(user, db)

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


@router.post("/google-login", response_model=schemas.Token)
def google_login(payload: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Google login endpoint.
    Verifies the Google ID token from Web, Android, or iOS and creates/retrieves the user.
    """
    try:
        # Obtener Client IDs
        google_client_id_web = os.getenv("GOOGLE_CLIENT_ID_WEB")
        google_client_id_android = os.getenv("GOOGLE_CLIENT_ID_ANDROID")
        
        # Al menos uno debe estar configurado
        if not google_client_id_web and not google_client_id_android:
            raise HTTPException(
                status_code=500,
                detail="Google Client IDs not configured"
            )
        
        # Intentar verificar el token con los Client IDs disponibles
        idinfo = None
        verification_error = None
        
        # Intentar primero con Web Client ID
        if google_client_id_web:
            try:
                idinfo = id_token.verify_oauth2_token(
                    payload.id_token,
                    requests.Request(),
                    google_client_id_web
                )
            except Exception as e:
                verification_error = e
        
        # Si falló con Web, intentar con Android Client ID
        if not idinfo and google_client_id_android:
            try:
                idinfo = id_token.verify_oauth2_token(
                    payload.id_token,
                    requests.Request(),
                    google_client_id_android
                )
            except Exception as e:
                verification_error = e
        
        # Si no se pudo verificar con ninguno, retornar error
        if not idinfo:
            print(f"[ERROR] Token verification failed: {verification_error}")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired Google token"
            )
        
        # Extraer información del usuario del token
        email = idinfo.get("email")
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")
        
        if not email:
            raise HTTPException(
                status_code=400,
                detail="Email not found in Google token"
            )
        
        # Buscar usuario existente
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if user:
            # Usuario existente - actualizar información si falta
            if not user.first_name and first_name:
                user.first_name = first_name
            if not user.last_name and last_name:
                user.last_name = last_name
            
            if user.blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your account has been blocked."
                )
            
            # Marcar como verificado si no lo estaba (google es confiable)
            if not user.is_verified:
                user.is_verified = True
                try:
                    send_welcome_email(
                        to_email=user.email,
                        username=user.first_name or user.username
                    )
                except Exception as e:
                    print(f"[MAIL] Error sending welcome email: {str(e)}")
        else:
            # Crear nuevo usuario
            # Generar username a partir del email
            username_base = email.split("@")[0]
            username = username_base
            counter = 1
            
            # Asegurar que el username sea único
            while db.query(models.User).filter(models.User.username == username).first():
                username = f"{username_base}{counter}"
                counter += 1
            
            user = models.User(
                email=email,
                username=username,
                hashed_password=security.hash_password(os.urandom(32).hex()),  # Contraseña aleatoria
                first_name=first_name,
                last_name=last_name,
                role="user",
                is_verified=True,  # Google verified
            )
            db.add(user)
            db.flush()
            
            # Enviar email de bienvenida
            try:
                send_welcome_email(
                    to_email=user.email,
                    username=user.first_name or user.username
                )
            except Exception as e:
                print(f"[MAIL] Error sending welcome email: {str(e)}")
        
        db.commit()
        db.refresh(user)
        
        # Generar JWT token
        token_data = {"sub": str(user.id), "email": user.email, "username": user.username}
        token = security.create_access_token(token_data)
        
        return {"access_token": token, "token_type": "bearer"}
        
    except ValueError as e:
        # Token inválido o expirado
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Google token"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Google login error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Google login failed: {str(e)}"
        )

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
    
    # Enviar email de bienvenida
    try:
        send_welcome_email(
            to_email=user.email,
            username=user.first_name or user.username
        )
    except Exception as e:
        print(f"[MAIL] Error sending welcome email: {str(e)}")
        # No lanzar excepción si el email de bienvenida falla
    
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification-email", response_model=dict)
def resend_verification_email(
    payload: schemas.ResendVerificationEmailRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user and not user.is_verified:
        _send_verification_email(user, db)

    return {
        "message": "If an account with that email exists and is not verified, a new verification email has been sent."
    }


@router.post("/verify-code", response_model=dict)
def verify_code(
    payload: schemas.VerifyCodeRequest,
    db: Session = Depends(get_db),
):
    """Verifica el código de verificación enviado por email"""
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )
    
    if user.is_verified:
        return {"message": "El correo ya está verificado. Puedes iniciar sesión."}
    
    # Verificar si el código existe
    if not user.verification_code:
        raise HTTPException(
            status_code=400,
            detail="No hay código de verificación enviado para esta cuenta"
        )
    
    # Verificar si el código ha expirado
    if user.verification_code_expires and user.verification_code_expires < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="El código ha expirado. Solicita uno nuevo."
        )
    
    # Verificar si el código es correcto (case-insensitive)
    if user.verification_code.lower() != payload.code.lower():
        raise HTTPException(
            status_code=400,
            detail="El código es incorrecto"
        )
    
    # Marcar como verificado y limpiar el código
    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    db.add(user)
    db.commit()
    
    # Enviar email de bienvenida
    try:
        send_welcome_email(
            to_email=user.email,
            username=user.first_name or user.username
        )
    except Exception as e:
        print(f"[MAIL] Error sending welcome email: {str(e)}")
        # No lanzar excepción si el email de bienvenida falla
    
    return {"message": "Correo verificado exitosamente. Ya puedes iniciar sesión."}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


def _send_reset_password_email(user: models.User, reset_token: str) -> None:
    app_url = os.getenv("APP_PUBLIC_URL", "http://localhost:5173")
    
    # Manejar esquemas personalizados (ej: bazaarfrontend://)
    if app_url.endswith("://"):
        link = f"{app_url}verify-reset?token={reset_token}"
    else:
        link = f"{app_url}/verify-reset?token={reset_token}"

    send_reset_password_email(
        to_email=user.email,
        username=user.first_name or user.username,
        reset_link=link
    )


@router.post("/request-reset-password", response_model=dict)
def request_reset_password(
    payload: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    
    if user:
        # Generar código aleatorio de 8 caracteres
        reset_code = generate_verification_code(length=8)
        
        # Guardar código en BD con expiración de 24 horas
        user.verification_code = reset_code
        user.verification_code_expires = datetime.utcnow() + timedelta(hours=24)
        db.add(user)
        db.commit()
        
        # Enviar email con código
        send_reset_password_email(
            to_email=user.email,
            username=user.first_name or user.username,
            reset_code=reset_code
        )

    # Retornar mensaje genérico por seguridad (no revelar si el email existe)
    return {
        "message": "If an account with that email exists, a password reset email has been sent."
    }


@router.post("/reset-password-with-code", response_model=dict)
def reset_password_with_code(
    payload: schemas.ResetPasswordWithCodeRequest,
    db: Session = Depends(get_db),
):
    """Verifica el código de reset y actualiza la contraseña"""
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )
    
    # Verificar si el código existe
    if not user.verification_code:
        raise HTTPException(
            status_code=400,
            detail="No hay código de reseteo enviado para esta cuenta"
        )
    
    # Verificar si el código ha expirado
    if user.verification_code_expires and user.verification_code_expires < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="El código ha expirado. Solicita uno nuevo."
        )
    
    # Verificar si el código es correcto (case-insensitive)
    if user.verification_code.lower() != payload.code.lower():
        raise HTTPException(
            status_code=400,
            detail="El código es incorrecto"
        )
    
    # Actualizar contraseña y limpiar el código
    user.hashed_password = security.hash_password(payload.new_password)
    user.verification_code = None
    user.verification_code_expires = None
    db.add(user)
    db.commit()

    return {"message": "Contraseña actualizada exitosamente. Ya puedes iniciar sesión con tu nueva contraseña."}


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
def forgot_password(
    payload: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Alias para /request-reset-password por compatibilidad"""
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user: 
        # Generar código aleatorio de 8 caracteres
        reset_code = generate_verification_code(length=8)
        
        # Guardar código en BD con expiración de 24 horas
        user.verification_code = reset_code
        user.verification_code_expires = datetime.utcnow() + timedelta(hours=24)
        db.add(user)
        db.commit()
        
        # Enviar email con código
        send_reset_password_email(
            to_email=user.email,
            username=user.first_name or user.username,
            reset_code=reset_code
        )
    return {"message": "If an account with that email exists, a password reset email has been sent."}

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user