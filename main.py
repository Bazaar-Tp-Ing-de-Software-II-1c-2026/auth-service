from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from loguru import logger

from app.database import engine, SessionLocal
from app import models
from app.api import auth, user
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.exceptions.handler import ServiceException, problem_details_handler
from app.logger import setup_logger

setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    logger.info("[STARTUP] Bazaar Auth Service iniciado")
    yield
    logger.info("[SHUTDOWN] Bazaar Auth Service detenido")


app = FastAPI(title="Bazaar Auth Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ServiceException, problem_details_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    errors = exc.errors()
    error_messages = []
    
    for error in errors:
        field = error.get("loc", [])[-1] if error.get("loc") else "unknown"
        error_type = error.get("type", "")
        msg = error.get("msg", "Invalid request data")
        
        # Detectar errores de email
        if "email" in str(field).lower() and "value_error" in error_type:
            error_messages.append("Formato de email inválido")
        # Detectar errores de contraseña
        elif "password" in str(field).lower() or "new_password" in str(field).lower():
            error_messages.append(msg)
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


app.include_router(auth.router)
app.include_router(user.router)


@app.get("/livez", tags=["health"])
def livez():
    """El proceso HTTP está vivo y puede recibir requests."""
    return {"status": "alive"}


@app.get("/readyz", tags=["health"])
def readyz():
    """El servicio puede operar: verifica conectividad con la base de datos."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        logger.debug("[READYZ] DB check OK")
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"[READYZ] DB check FAILED: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "type": "about:blank",
                "title": "Service Unavailable",
                "status": 503,
                "detail": "Database connection failed",
                "instance": "/readyz",
            },
            media_type="application/problem+json",
        )
    finally:
        db.close()