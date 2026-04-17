from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import json


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)

        except RequestValidationError as exc:
            # Extraer información del error de validación
            errors = exc.errors()
            error_messages = []
            
            for error in errors:
                field = error.get("loc", [])[-1] if error.get("loc") else "unknown"
                error_type = error.get("type", "")
                msg = error.get("msg", "Dato inválido")
                
                # Detectar errores de email
                if "email" in str(field).lower() and "value_error" in error_type:
                    error_messages.append("Formato de email inválido")
                # Detectar errores de contraseña - Pydantic devuelve el ValueError message en msg
                elif "password" in str(field).lower() or "new_password" in str(field).lower():
                    # El mensaje ya contiene el error específico del validador
                    if msg:
                        error_messages.append(msg)
                    else:
                        error_messages.append("Contraseña inválida")
                else:
                    error_messages.append(msg)
            
            detail = " | ".join(error_messages) if error_messages else "Invalid request data"
            
            return JSONResponse(
                status_code=400,
                content={
                    "type": "about:blank",
                    "title": "Bad request error",
                    "status": 400,
                    "detail": detail,
                    "instance": str(request.url.path),
                },
                media_type="application/problem+json",
            )

        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "type": "about:blank",
                    "title": "HTTP error",
                    "status": exc.status_code,
                    "detail": exc.detail,
                    "instance": str(request.url.path),
                },
                media_type="application/problem+json",
            )

        except Exception as e:
            logger.error(f"[MIDDLEWARE] Unhandled exception: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "type": "about:blank",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "An unexpected error occurred",
                    "instance": str(request.url.path),
                },
                media_type="application/problem+json",
            )