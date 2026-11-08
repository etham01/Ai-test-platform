from __future__ import annotations

import contextlib
import logging
import secrets
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecretConfigurationError(RuntimeError):
    """Raised when the application encryption key is missing or invalid."""


def _fernet_key() -> bytes:
    if settings.secret_key:
        return settings.secret_key.encode("utf-8")

    path: Path = settings.secret_key_file
    if path.exists():
        return path.read_bytes().strip()

    if not settings.is_development:
        raise SecretConfigurationError(
            "SMARTTEST_SECRET_KEY is required outside development; refusing to start with "
            "an auto-generated key."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    path.write_bytes(key)
    with contextlib.suppress(OSError):
        path.chmod(0o600)
    logger.warning(
        "Generated development encryption key at %s. Do not commit it; production must set "
        "SMARTTEST_SECRET_KEY.",
        path,
    )
    return key


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    try:
        return Fernet(_fernet_key())
    except (ValueError, TypeError) as exc:
        raise SecretConfigurationError(
            "SMARTTEST_SECRET_KEY is not a valid Fernet key (expected 32 url-safe base64 bytes)."
        ) from exc


def encrypt_secret(value: str) -> str:
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    try:
        return get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise SecretConfigurationError(
            "Stored secret cannot be decrypted with the current encryption key."
        ) from exc


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


def constant_time_equals(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return secrets.compare_digest(left, right)
