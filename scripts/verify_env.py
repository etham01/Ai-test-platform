#!/usr/bin/env python
"""Verify the local SmartTest development environment.

Run from the repository root:
    .venv/Scripts/python.exe scripts/verify_env.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from redis import Redis  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine.url import make_url  # noqa: E402

from app.core.config import settings  # noqa: E402


def check_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        return f"{name}: NOT FOUND"
    try:
        command = f'"{path}" --version'
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=True,
        )
        output = (result.stdout or result.stderr).strip()
        version = output.splitlines()[0] if output else "(no version output)"
    except Exception as exc:  # pragma: no cover - diagnostic helper
        version = f"error: {exc}"
    return f"{name}: {version} ({path})"


def main() -> int:
    failures = 0
    print("== SmartTest environment check ==")
    print(f"project root: {ROOT}")
    print(f".env present: {(ROOT / '.env').exists()}")
    print(f"storage root: {settings.storage_root}")
    print(f"database: {make_url(settings.database_url).render_as_string(hide_password=True)}")
    print(f"redis: {make_url(settings.redis_url).render_as_string(hide_password=True)}")
    print()

    print("-- toolchain --")
    print(check_command("python"))
    print(check_command("node"))
    print(check_command("npm"))
    print(check_command("pnpm"))
    print()

    print("-- database --")
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            tables = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE()"
                )
            ).scalar_one()
        print(f"MySQL: OK (tables in current schema: {tables})")
        engine.dispose()
    except Exception as exc:
        print(f"MySQL: FAIL ({type(exc).__name__}: {str(exc).splitlines()[0][:300]})")
        failures += 1

    print()
    print("-- redis --")
    client = None
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        print(f"Redis: OK (PING -> {client.ping()})")
    except Exception as exc:
        print(f"Redis: FAIL ({type(exc).__name__}: {str(exc)[:300]})")
        failures += 1
    finally:
        if client is not None:
            client.close()

    print()
    print("-- browser --")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser_path = Path(playwright.chromium.executable_path)
        if browser_path.exists():
            print(f"Playwright chromium: OK ({browser_path})")
        else:
            print(f"Playwright chromium: NOT INSTALLED ({browser_path})")
            print("  fallback: set PLAYWRIGHT_CHANNEL=chrome in .env")
    except Exception as exc:
        print(f"Playwright: FAIL ({type(exc).__name__}: {str(exc)[:300]})")

    chrome_candidates = [
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    ]
    for candidate in chrome_candidates:
        if candidate.exists():
            print(f"system browser: {candidate}")
            break

    print()
    print("-- storage --")
    for relative in ("projects", "executions"):
        path = settings.storage_root / relative
        print(f"{path}: {'OK' if path.exists() else 'MISSING'}")

    print()
    if failures:
        print(f"RESULT: {failures} blocking dependency check(s) failed.")
        return 1
    print("RESULT: blocking dependencies OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
