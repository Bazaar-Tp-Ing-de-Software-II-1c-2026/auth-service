from __future__ import annotations
import os
from fastapi import HTTPException, status

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