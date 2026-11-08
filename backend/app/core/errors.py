from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, get_request_id

logger = get_logger(__name__)


class AppError(Exception):
    """Expected business/API error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(code, message, status_code=404, details=details)


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(code, message, status_code=409, details=details)


class ForbiddenError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(code, message, status_code=403, details=details)


class UnauthorizedError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(code, message, status_code=401, details=details)


class UpstreamError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(code, message, status_code=502, details=details)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or get_request_id()


def error_payload(
    code: str,
    message: str,
    details: Any | None,
    request_id: str | None,
) -> dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": jsonable_encoder(details) if details is not None else None,
        },
        "request_id": request_id,
    }


def error_response(
    request: Request,
    code: str,
    message: str,
    status_code: int,
    details: Any | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, details, _request_id(request)),
        headers={"X-Request-ID": _request_id(request) or ""},
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            request, exc.code, exc.message, exc.status_code, exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = []
        for error in exc.errors():
            item = {key: value for key, value in error.items() if key != "ctx"}
            details.append(item)
        return error_response(
            request,
            "VALIDATION_ERROR",
            "请求参数校验失败",
            422,
            details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            code = str(detail.get("code", "HTTP_ERROR"))
            message = str(detail.get("message", detail))
            details = detail.get("details")
        else:
            code = "HTTP_ERROR"
            message = str(detail)
            details = None
        return error_response(request, code, message, exc.status_code, details)

    @app.exception_handler(Exception)
    async def handle_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return error_response(
            request,
            "INTERNAL_ERROR",
            "服务内部错误，请查看服务端日志",
            500,
        )
