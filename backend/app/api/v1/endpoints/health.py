from __future__ import annotations

import contextlib
import time
from typing import Any

from fastapi import APIRouter
from redis import Redis

from app.core.config import settings
from app.core.logging import get_request_id
from app.db.session import check_database
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/health", tags=["health"])


def _check_redis() -> dict[str, Any]:
    started = time.perf_counter()
    client: Redis | None = None
    try:
        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
            protocol=2,
        )
        client.ping()
        return {
            "ok": True,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc).splitlines()[0][:300]}
    finally:
        if client is not None:
            with contextlib.suppress(Exception):
                client.close()


@router.get("/deps", response_model=ApiResponse[dict[str, Any]], summary="依赖健康检查")
def dependency_health() -> ApiResponse[dict[str, Any]]:
    database = check_database()
    redis_status = _check_redis()
    return ApiResponse(
        data={
            "ok": bool(database.get("ok")) and bool(redis_status.get("ok")),
            "database": database,
            "redis": redis_status,
        },
        request_id=get_request_id(),
    )
