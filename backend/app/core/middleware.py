from __future__ import annotations

import re
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import reset_request_id, set_request_id
from app.core.security import constant_time_equals

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,96}$")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(settings.request_id_header)
        request_id = (
            incoming
            if incoming and _REQUEST_ID_RE.fullmatch(incoming)
            else f"req_{uuid.uuid4().hex}"
        )
        request.state.request_id = request_id
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
            response.headers[settings.request_id_header] = request_id
            return response
        finally:
            reset_request_id(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response


class ApiTokenMiddleware(BaseHTTPMiddleware):
    """Optional lightweight gate for non-local deployments.

    Disabled when SMARTTEST_API_TOKEN is empty. It is not a replacement for real
    authentication; see docs/SECURITY.md.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.api_token:
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        protected = path.startswith(settings.api_v1_prefix) and not path.startswith(
            f"{settings.api_v1_prefix}/health"
        )
        if not protected:
            return await call_next(request)

        supplied = request.headers.get("X-API-Token")
        if constant_time_equals(supplied, settings.api_token):
            return await call_next(request)

        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "缺少或错误的 X-API-Token",
                    "details": None,
                },
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id or ""},
        )
