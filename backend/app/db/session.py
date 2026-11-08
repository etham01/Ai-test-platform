from __future__ import annotations

import time
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)


@event.listens_for(engine, "connect")
def _set_mysql_session_timezone(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
    if engine.dialect.name != "mysql":
        return
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET time_zone = '+00:00'")


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> dict[str, object]:
    started = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"ok": True, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except Exception as exc:  # pragma: no cover - exercised by health endpoint
        return {"ok": False, "error": str(exc).splitlines()[0][:300]}


def dispose_engine() -> None:
    engine.dispose()
