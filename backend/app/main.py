"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (ensure models are registered on Base)
from .config import settings
from .database import Base, engine
from .logging_config import setup_logging
from .routers import certificates, dashboard, imports, monitors, notifications
from .scheduler import shutdown_scheduler, start_scheduler

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.app_name)
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Certificate management & TLS expiry monitoring API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(certificates.router)
app.include_router(monitors.router)
app.include_router(dashboard.router)
app.include_router(imports.router)
app.include_router(notifications.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.app_name, "version": "1.0.0"}
