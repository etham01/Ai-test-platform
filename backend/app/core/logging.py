from __future__ import annotations

import contextvars
import logging
import re
import sys

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "smarttest_request_id", default=None
)
_task_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "smarttest_task_id", default=None
)

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[A-Za-z0-9._~+/=-]+"),
        r"\1<redacted>",
    ),
    (
        re.compile(
            r"(?i)\b(api[_-]?key|authorization|password|passwd|token|secret|cookie)\b"
            r"(\s*[=:]\s*)(?!bearer\b|<redacted>)([\"']?)([^\s\"',;]+)"
        ),
        r"\1\2\3<redacted>",
    ),
    (re.compile(r"sk-[A-Za-z0-9_-]{8,}"), "sk-<redacted>"),
    (re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer <redacted>"),
    (re.compile(r"mysql\+pymysql://[^\s]+"), "mysql+pymysql://<redacted>"),
    (re.compile(r"redis://[^\s]+"), "redis://<redacted>"),
)


def redact_text(value: str) -> str:
    text = value
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def set_request_id(value: str | None) -> contextvars.Token[str | None]:
    return _request_id.set(value)


def reset_request_id(token: contextvars.Token[str | None]) -> None:
    _request_id.reset(token)


def set_task_id(value: str | None) -> contextvars.Token[str | None]:
    return _task_id.set(value)


def reset_task_id(token: contextvars.Token[str | None]) -> None:
    _task_id.reset(token)


def get_request_id() -> str | None:
    return _request_id.get()


def get_task_id() -> str | None:
    return _task_id.get()


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        record.task_id = get_task_id() or "-"
        return True


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact_text(super().format(record))


def setup_logging(level: str | None = None) -> None:
    root = logging.getLogger()
    if getattr(root, "_smarttest_configured", False):
        return
    root.setLevel((level or "INFO").upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RedactingFormatter(
            "%(asctime)s %(levelname)-7s %(name)s "
            "[request_id=%(request_id)s] [task_id=%(task_id)s] %(message)s"
        )
    )
    handler.addFilter(_ContextFilter())
    root.addHandler(handler)
    root._smarttest_configured = True  # type: ignore[attr-defined]
    # Keep noisy third-party loggers at warning level unless debugging.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
