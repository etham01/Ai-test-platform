from __future__ import annotations

import re
from pathlib import Path

from app.core.config import settings

_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class PathSecurityError(ValueError):
    """Raised when a user-supplied path could escape the storage root."""


def ensure_storage_dirs() -> None:
    for relative in ("projects", "executions", "tmp"):
        (settings.storage_root / relative).mkdir(parents=True, exist_ok=True)


def resolve_within(root: Path, relative: str | Path) -> Path:
    """Resolve a relative path under root and reject traversal/absolute paths."""
    if relative is None:
        raise PathSecurityError("empty path")
    raw = str(relative)
    if not raw or "\x00" in raw:
        raise PathSecurityError("invalid path")
    candidate = Path(raw)
    if candidate.is_absolute() or candidate.drive:
        raise PathSecurityError("absolute paths are not allowed")
    if ".." in candidate.parts:
        raise PathSecurityError("parent traversal is not allowed")

    root_resolved = root.resolve()
    target = (root_resolved / candidate).resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise PathSecurityError("path escapes storage root")
    return target


def relative_posix(path: Path, root: Path | None = None) -> str:
    root_resolved = (root or settings.storage_root).resolve()
    return path.resolve().relative_to(root_resolved).as_posix()


def safe_filename(name: str, default: str = "file", max_length: int = 128) -> str:
    """Return a conservative ASCII filename (no directories, no traversal)."""
    base = Path(str(name)).name
    cleaned = _SAFE_NAME.sub("_", base).strip(" ._")
    if not cleaned:
        cleaned = default
    stem = Path(cleaned).stem.upper()
    if stem in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned[:max_length]
