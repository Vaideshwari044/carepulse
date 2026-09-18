"""CarePulse FastAPI application entry point."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import asyncpg
import structlog
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)


def _asyncpg_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+asyncpg://")
    return database_url


async def _run_migrations():
    """Run Alembic migrations on startup."""
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd="/app",
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.info("migrations.success")
        else:
            logger.error("migrations.failed", stderr=result.stderr[:500])
    except Exception as exc:
        logger.error("migrations.error", error=str(exc))


async def _seed_database():
    """Run seed script."""
    try:
        from app.seed import seed_database
        await seed_database()
    except Exception as exc:
        logger.error("seed.error", error=str(exc))


async def _load_ml_model():
    """Load ML model if available."""
    try:
        settings = get_settings()
        from app.ml.inference import ml_inference
        loaded = ml_inference.load_model(settings.MODEL_PATH)
        if loaded:
            logger.info("ml.model_ready", version=ml_inference.model_version)
        else:
            logger.info("ml.fallback_mode", model_path=settings.MODEL_PATH)
    except Exception as exc:
        logger.error("ml.load_error", error=str(exc))


async def _database_status(database_url: str) -> str:
    try:
        conn = await asyncpg.connect(dsn=_asyncpg_dsn(database_url), timeout=3)
        try:
            await conn.execute("SELECT 1")
        finally:
            await conn.close()
        return "ok"
    except Exception as exc:
        logger.error("health.database_check_failed", error=str(exc))
        return "error"


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    settings = get_settings()
    logger.info("carepulse.startup", phase="production")

    await _run_migrations()
    await _seed_database()
    await _load_ml_model()

    yield
    logger.info("carepulse.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="CarePulse",
        description=(
            "AI-assisted early-warning decision-support system. "
            "NOT a diagnostic device. NOT clinically validated. NOT for patient care. "
            "Synthetic and replayed data only."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Health endpoint ─────────────────────────────────────────────────────
    @application.get("/health")
    async def health():
        from app.ml.inference import ml_inference
        db_status = await _database_status(settings.DATABASE_URL)
        model_status = "ready" if ml_inference.is_ready() else "fallback"
        overall = "ok" if db_status == "ok" else "degraded"
        return {
            "status": overall,
            "database": db_status,
            "model": model_status,
            "monitoring": "ok",
            "safety_note": "RESEARCH DATA / SYNTHETIC DEMO — NOT CLINICALLY VALIDATED",
        }


    # ─── API v1 routes ───────────────────────────────────────────────────────
    api_prefix = "/api/v1"

    from app.routers.auth import router as auth_router
    from app.routers.patients import router as patients_router
    from app.routers.vitals import router as vitals_router
    from app.routers.monitoring import router as monitoring_router
    from app.routers.alerts import router as alerts_router
    from app.routers.clinical import router as clinical_router
    from app.routers.analytics import router as analytics_router
    from app.routers.chatbot import router as chatbot_router
    from app.routers.datasets import router as datasets_router
    from app.routers.tasks import router as tasks_router
    from app.routers.reports import router as reports_router
    from app.routers.audit import router as audit_router

    application.include_router(auth_router, prefix=api_prefix)
    application.include_router(patients_router, prefix=api_prefix)
    application.include_router(vitals_router, prefix=api_prefix)
    application.include_router(monitoring_router, prefix=api_prefix)
    application.include_router(alerts_router, prefix=api_prefix)
    application.include_router(clinical_router, prefix=api_prefix)
    application.include_router(analytics_router, prefix=api_prefix)
    application.include_router(chatbot_router, prefix=api_prefix)
    application.include_router(datasets_router, prefix=api_prefix)
    application.include_router(tasks_router, prefix=api_prefix)
    application.include_router(reports_router, prefix=api_prefix)
    application.include_router(audit_router, prefix=api_prefix)

    # ─── WebSocket ──────────────────────────────────────────────────────────
    @application.websocket("/ws/monitoring")
    async def ws_monitoring(websocket: WebSocket, token: str = ""):
        from app.ws.manager import websocket_endpoint
        await websocket_endpoint(websocket, token)

    # ─── Global error handler ────────────────────────────────────────────────
    @application.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        logger.error("unhandled_exception", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred", "details": {}}},
        )

    return application


app = create_app()
