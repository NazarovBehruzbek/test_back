import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import django
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.dependencies import DbSession
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.db.base import import_models
from app.db.session import get_engine
from django_admin.asgi import application as django_admin_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize logging/models on startup and dispose DB pool on shutdown."""
    settings = get_settings()
    setup_logging(debug=settings.DEBUG)
    import_models()
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.ENVIRONMENT)
    yield
    await get_engine().dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AqlliOlam — Korporativ tashrifchilarni boshqarish tizimi REST API",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    admin_static_dir = Path(django.__file__).resolve().parent / "contrib" / "admin" / "static"
    application.mount("/static", StaticFiles(directory=admin_static_dir), name="django-static")
    application.mount("/admin", django_admin_app)

    @application.get("/health", tags=["Health"], summary="Tizim holatini tekshirish")
    async def health_check(db: DbSession) -> JSONResponse:
        try:
            await db.execute(text("SELECT 1"))
            return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})
        except Exception as exc:
            logger.exception("Database health check failed", exc_info=exc)
            return JSONResponse(
                status_code=503,
                content={"status": "degraded", "database": "unavailable"},
            )

    return application


app = create_app()
