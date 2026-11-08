from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    ApiTokenMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.paths import ensure_storage_dirs
from app.db.session import dispose_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    ensure_storage_dirs()
    if not settings.is_development and not settings.secret_key:
        raise RuntimeError(
            "SMARTTEST_SECRET_KEY is required when APP_ENV is not development."
        )
    if settings.api_token:
        logger.info("API token gate is enabled")
    logger.info(
        "Starting %s v%s (env=%s, storage=%s)",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        settings.storage_root,
    )
    yield
    dispose_engine()


def create_app() -> FastAPI:
    setup_logging(settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Intelligent multi-page Web test case and script generation platform.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[settings.request_id_header],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ApiTokenMiddleware)
    # Added last so it is the outermost middleware and every response gets the ID.
    app.add_middleware(RequestIdMiddleware)

    install_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["meta"])
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "docs": "/docs", "health": "/health"}

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
        }

    return app


app = create_app()
