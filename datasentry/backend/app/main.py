from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import (
    alerts,
    annotations,
    audit,
    auth,
    charts,
    cleaning,
    connectors,
    datasets,
    drift,
    insights,
    models_v4,
    monitoring,
    profiling,
    public,
    reports,
    teams,
    training,
    usage,
    webhooks,
)
from app.core.config import settings
from app.core.middleware import UsageMiddleware
from app.db.session import init_db

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_production:
        if settings.JWT_SECRET == "change-me-in-production":
            raise RuntimeError("JWT_SECRET must be set to a strong value in production.")
        if settings.uses_sqlite:
            raise RuntimeError("Production must use PostgreSQL, not SQLite.")

    if settings.uses_sqlite:
        init_db()
    else:
        _run_migrations()
    yield


app = FastAPI(title="DataSentry API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(UsageMiddleware)


@app.exception_handler(HTTPException)
async def http_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error_code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content={"error_code": "HTTP_ERROR", "message": str(detail)})


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    # SRS-8.2: never leak raw stack traces to the client.
    logging.getLogger(__name__).exception("unhandled error")
    return JSONResponse(status_code=500, content={"error_code": "INTERNAL_ERROR", "message": "An internal error occurred."})


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    try:
        cfg = Config("alembic.ini")
        cfg.set_main_option("script_location", "migrations")
        cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        command.upgrade(cfg, "head")
        logging.getLogger(__name__).info("Database migrated to head.")
    except Exception:
        logging.getLogger(__name__).exception("Migration failed; continuing with create_all fallback.")
        init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


for r in (datasets, profiling, insights, cleaning, charts, reports):
    app.include_router(r.router, prefix="/api/v1")

# v2–v4 surfaces
for r in (auth, connectors, drift, training, alerts, monitoring, public, teams, annotations, webhooks, models_v4, audit, usage):
    app.include_router(r.router, prefix="/api/v1")
