from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from app.core.config import settings

logger = logging.getLogger(__name__)


class BrowserLaunchError(RuntimeError):
    pass


@dataclass
class BrowserSession:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page

    def close(self) -> None:
        for action in (self.context.close, self.browser.close, self.playwright.stop):
            with contextlib.suppress(Exception):
                action()


class BrowserManager:
    """Launch one Chromium-family browser/context for a scan or test run.

    The context is reused for all pages in a scan so cookies/session state stay
    consistent. A fresh manager is used per task; nothing is shared globally.
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        *,
        headless: bool = True,
        storage_state: dict[str, Any] | str | None = None,
        channel: str | None = None,
        viewport_width: int = 1440,
        viewport_height: int = 1000,
    ) -> None:
        self.browser_type = browser_type
        self.headless = headless
        self.storage_state = storage_state
        self.channel = channel
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._session: BrowserSession | None = None

    def _resolve_channel(self) -> str | None:
        if self.browser_type == "chrome":
            return "chrome"
        if self.browser_type == "msedge":
            return "msedge"
        return self.channel or settings.browser_channel

    def __enter__(self) -> BrowserSession:
        playwright = sync_playwright().start()
        channel = self._resolve_channel()
        browser: Browser | None = None
        try:
            try:
                browser = playwright.chromium.launch(headless=self.headless, channel=channel)
            except Exception as exc:
                if channel is None:
                    logger.warning(
                        "Bundled Chromium launch failed (%s); falling back to system Chrome",
                        exc,
                    )
                    browser = playwright.chromium.launch(headless=self.headless, channel="chrome")
                    channel = "chrome"
                else:
                    raise BrowserLaunchError(
                        f"无法启动浏览器（channel={channel}）：{exc}"
                    ) from exc

            context = browser.new_context(
                viewport={"width": self.viewport_width, "height": self.viewport_height},
                locale="zh-CN",
                storage_state=self.storage_state,
                ignore_https_errors=False,
            )
            page = context.new_page()
            page.set_default_timeout(15_000)
            self._session = BrowserSession(playwright, browser, context, page)
            return self._session
        except Exception:
            if browser is not None:
                with contextlib.suppress(Exception):
                    browser.close()
            with contextlib.suppress(Exception):
                playwright.stop()
            raise

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._session is not None:
            self._session.close()
            self._session = None
