"""
Utilidades para generación y verificación de códigos
"""
import string
import secrets
from datetime import datetime, timezone


def generate_verification_code(length: int = 8) -> str:
    """
    Genera un código de verificación aleatorio con mayúsculas, minúsculas, números y caracteres especiales.
    
    Args:
        length: Longitud del código a generar (default: 8)
    
    Returns:
        str: Código aleatorio generado
    """
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))


def is_code_expired(expires_at: datetime) -> bool:
    """
    Verifica si un código ha expirado.
    
    Args:
        expires_at: Datetime de expiración del código
    
    Returns:
        bool: True si ha expirado, False si aún es válido
    """
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > expires_at
