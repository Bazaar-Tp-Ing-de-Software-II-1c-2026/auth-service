from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from loguru import logger

from app.database import engine, SessionLocal
from app import models
from app.api import auth, user, addresses, pin, push_tokens
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
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()

    invalid_params = []
    messages = []

    for err in errors:
        location = err["loc"][0] if err.get("loc") else "unknown"
        msg = err.get("msg", "Invalid request data")
        error_type = err.get("type", "")

        if isinstance(msg, str) and msg.startswith("Value error, "):
            msg = msg.replace("Value error, ", "", 1)

        messages.append(msg)

        invalid_params.append({
            "in": location,
            "name": ".".join(map(str, err["loc"][1:])),
            "reason": msg,
            "type": error_type,
        })

    detail = " | ".join(messages) if messages else "Invalid request data"

    return JSONResponse(
        status_code=400,
        content={
            "type": "about:blank",
            "title": "Invalid request parameters",
            "status": 400,
            "detail": detail,  # 👈 humano
            "instance": str(request.url.path),
            "invalid-params": invalid_params,  # 👈 estructurado
        },
        media_type="application/problem+json",
    )


app.include_router(auth.router)
app.include_router(user.router)
app.include_router(addresses.router)
app.include_router(pin.router)
app.include_router(push_tokens.router)


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