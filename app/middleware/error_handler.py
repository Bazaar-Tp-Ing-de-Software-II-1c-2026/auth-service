from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)

        except RequestValidationError:
            return JSONResponse(
                status_code=400,
                content={
                    "type": "about:blank",
                    "title": "Bad request error",
                    "status": 400,
                    "detail": "Invalid request data",
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