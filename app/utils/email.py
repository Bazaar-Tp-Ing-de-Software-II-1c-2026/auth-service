from __future__ import annotations
import os
from fastapi import HTTPException, status
from .email_templates import (
    get_verification_email_html,
    get_reset_password_email_html,
    get_welcome_email_html
)

try:
    import resend
except ImportError:
    resend = None


def send_email_html(
    to_email: str, subject: str, html_body: str, text_fallback: str | None = None
):
    """Send email using Resend API"""
    api_key = os.getenv("RESEND_API_KEY")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RESEND_API_KEY no configurada"
        )
    
    if not resend:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Librería resend no instalada"
        )
    
    resend.api_key = api_key
    from_email = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
    
    try:
        r = resend.Emails.send({
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "html": html_body,
            "text": text_fallback or "Tu cliente de correo no soporta HTML."
        })
        
        if r.get("id"):
            print(f"[MAIL] Email enviado exitosamente: {r['id']}")
        else:
            error_msg = r.get("message", "Error desconocido")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error enviando email: {error_msg}"
            )
    except Exception as e:
        print(f"[MAIL] Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error enviando email: {str(e)}"
        )


def send_verification_email(
    to_email: str, username: str, verification_code: str
):
    """Enviar email de verificación con código personalizado"""
    html_content = get_verification_email_html(username, verification_code)
    send_email_html(
        to_email=to_email,
        subject="Verifica tu cuenta - Bazaar",
        html_body=html_content
    )


def send_reset_password_email(
    to_email: str, username: str, reset_link: str
):
    """Enviar email de reseteo de contraseña con template personalizado"""
    html_content = get_reset_password_email_html(username, reset_link)
    send_email_html(
        to_email=to_email,
        subject="Restablecer tu contraseña - Bazaar",
        html_body=html_content
    )


def send_welcome_email(to_email: str, username: str):
    """Enviar email de bienvenida (opcional)"""
    html_content = get_welcome_email_html(username)
    send_email_html(
        to_email=to_email,
        subject="¡Bienvenido a Bazaar!",
        html_body=html_content
    )