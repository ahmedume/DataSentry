from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _normalize_db_url(url: str) -> str:
    # SQLAlchemy needs an explicit driver; map the bare postgresql:// scheme
    # to the psycopg (v3) driver so we don't depend on psycopg2.
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


_database_url = _normalize_db_url(settings.DATABASE_URL)
connect_args = {}
if _database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(_database_url, connect_args=connect_args, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.db import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
