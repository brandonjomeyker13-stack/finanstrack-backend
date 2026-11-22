import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.db.session import engine

logging.basicConfig(level=logging.INFO if settings.is_production else logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ESTADO = {
    NotFoundError: 404,
    ConflictError: 409,
    UnauthorizedError: 401,
    ForbiddenError: 403,
    ValidationError: 422,
}


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError):
    cuerpo: dict[str, str] = {"detail": exc.message}
    if exc.codigo:
        cuerpo["codigo"] = exc.codigo
    return JSONResponse(status_code=_ESTADO.get(type(exc), 400), content=cuerpo)


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def raiz():
    return {"nombre": settings.PROJECT_NAME, "salud": "/health"}


@app.get("/health")
def health_check():
    """¿Está vivo el proceso? Render usa esto para saber si arrancó.

    No toca la base: un parpadeo de Supabase reiniciaría el servicio en bucle.
    """
    return {"status": "ok"}


@app.get("/listo")
def readiness_check():
    """¿Puede atender de verdad? Esto sí pregunta a la base.

    De paso mantiene despierto el proyecto de Supabase, que en el plan
    gratuito se pausa si nadie lo toca por unos días.
    """
    try:
        with engine.connect() as conexion:
            conexion.execute(text("SELECT 1"))
    except Exception:
        logger.exception("La base no respondió")
        return JSONResponse(status_code=503, content={"status": "sin_base"})
    return {"status": "listo"}
