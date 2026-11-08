from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.browser.browser_manager import BrowserManager
from app.browser.page_parser import PageParser, ParsedForm, ParsedLink, ParsedPage
from app.browser.url_policy import URLPolicy, URLPolicyError, normalize_url


class ExplorationCancelled(RuntimeError):
    pass


class ExplorationTimeout(RuntimeError):
    pass


@dataclass
class ExplorerConfig:
    start_url: str
    max_pages: int = 8
    max_depth: int = 2
    page_timeout_seconds: int = 15
    total_timeout_seconds: int = 300
    wait_after_load_ms: int = 800
    browser_type: str = "chromium"
    extra_urls: list[str] = field(default_factory=list)


@dataclass
class ExploredPage:
    requested_url: str
    normalized_url: str
    final_url: str
    depth: int
    discovered_from_url: str | None
    source: str
    status: str
    parsed: ParsedPage | None = None
    links: list[ParsedLink] = field(default_factory=list)
    form_actions: list[ParsedForm] = field(default_factory=list)
    error: str | None = None


class SiteExplorer:
    def __init__(self, config: ExplorerConfig, policy: URLPolicy) -> None:
        self.config = config
        self.policy = policy

    def _check_limits(
        self,
        started_at: float,
        should_cancel: Callable[[], bool] | None,
    ) -> None:
        if should_cancel is not None and should_cancel():
            raise ExplorationCancelled("任务已取消")
        elapsed = time.monotonic() - started_at
        if elapsed >= self.config.total_timeout_seconds:
            raise ExplorationTimeout("站点探索超过总超时时间")

    def _form_actions(self, parsed: ParsedPage, current_url: str) -> list[ParsedForm]:
        actions: list[ParsedForm] = []
        for form in parsed.forms:
            action = form.action or current_url
            try:
                target = self.policy.validate(normalize_url(action, current_url))
            except URLPolicyError:
                continue
            actions.append(
                ParsedForm(action=target, method=form.method, fields=form.fields)
            )
        return actions

    def explore(
        self,
        on_page: Callable[[ExploredPage], None],
        on_progress: Callable[[int, int, str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        started_at = time.monotonic()
        start_url = self.policy.validate(self.config.start_url)
        queue: deque[tuple[str, int, str | None, str]] = deque(
            [(start_url, 0, None, "start")]
        )
        scheduled = {start_url}

        for extra in self.config.extra_urls:
            try:
                extra_url = self.policy.validate(normalize_url(extra, start_url))
            except URLPolicyError:
                continue
            if extra_url not in scheduled:
                scheduled.add(extra_url)
                queue.append((extra_url, 1, start_url, "manual"))

        visited: set[str] = set()
        pages_done = 0

        if on_progress:
            on_progress(0, self.config.max_pages, "开始探索")

        with BrowserManager(self.config.browser_type) as session:
            while queue and pages_done < self.config.max_pages:
                self._check_limits(started_at, should_cancel)
                requested_url, depth, from_url, source = queue.popleft()
                if requested_url in visited:
                    continue
                visited.add(requested_url)

                page = session.page
                try:
                    response = page.goto(
                        requested_url,
                        wait_until="domcontentloaded",
                        timeout=self.config.page_timeout_seconds * 1000,
                    )
                    if self.config.wait_after_load_ms > 0:
                        page.wait_for_timeout(min(self.config.wait_after_load_ms, 5000))

                    final_url = normalize_url(page.url)
                    try:
                        final_url = self.policy.validate(final_url)
                    except URLPolicyError as exc:
                        pages_done += 1
                        on_page(
                            ExploredPage(
                                requested_url=requested_url,
                                normalized_url=requested_url,
                                final_url=page.url,
                                depth=depth,
                                discovered_from_url=from_url,
                                source=source,
                                status="blocked",
                                error=exc.message,
                            )
                        )
                        if on_progress:
                            on_progress(pages_done, self.config.max_pages, "页面被策略阻止")
                        continue

                    parsed = PageParser.parse(page, response)
                    allowed_links: list[ParsedLink] = []
                    for link in parsed.links:
                        target = self.policy.resolve_link(link.href, final_url)
                        if target is not None:
                            allowed_links.append(ParsedLink(href=target, text=link.text))
                    form_actions = self._form_actions(parsed, final_url)

                    pages_done += 1
                    on_page(
                        ExploredPage(
                            requested_url=requested_url,
                            normalized_url=final_url,
                            final_url=page.url,
                            depth=depth,
                            discovered_from_url=from_url,
                            source=source,
                            status="parsed",
                            parsed=parsed,
                            links=allowed_links,
                            form_actions=form_actions,
                        )
                    )
                    if on_progress:
                        on_progress(
                            pages_done,
                            self.config.max_pages,
                            f"已采集 {pages_done}/{self.config.max_pages} 个页面",
                        )

                    if depth < self.config.max_depth:
                        for link in allowed_links:
                            if link.href in scheduled or link.href in visited:
                                continue
                            scheduled.add(link.href)
                            queue.append((link.href, depth + 1, final_url, "link"))
                except PlaywrightTimeoutError as exc:
                    pages_done += 1
                    on_page(
                        ExploredPage(
                            requested_url=requested_url,
                            normalized_url=requested_url,
                            final_url=page.url if page else requested_url,
                            depth=depth,
                            discovered_from_url=from_url,
                            source=source,
                            status="failed",
                            error=f"页面加载超时: {exc}"[:2000],
                        )
                    )
                    if on_progress:
                        on_progress(pages_done, self.config.max_pages, "页面加载超时")
                except URLPolicyError as exc:
                    pages_done += 1
                    on_page(
                        ExploredPage(
                            requested_url=requested_url,
                            normalized_url=requested_url,
                            final_url=requested_url,
                            depth=depth,
                            discovered_from_url=from_url,
                            source=source,
                            status="blocked",
                            error=exc.message,
                        )
                    )
                except PlaywrightError as exc:
                    pages_done += 1
                    on_page(
                        ExploredPage(
                            requested_url=requested_url,
                            normalized_url=requested_url,
                            final_url=requested_url,
                            depth=depth,
                            discovered_from_url=from_url,
                            source=source,
                            status="failed",
                            error=f"浏览器错误: {exc}"[:2000],
                        )
                    )
                except Exception as exc:  # pragma: no cover - defensive per-page path
                    pages_done += 1
                    on_page(
                        ExploredPage(
                            requested_url=requested_url,
                            normalized_url=requested_url,
                            final_url=requested_url,
                            depth=depth,
                            discovered_from_url=from_url,
                            source=source,
                            status="failed",
                            error=f"{type(exc).__name__}: {exc}"[:2000],
                        )
                    )

        if on_progress:
            on_progress(pages_done, self.config.max_pages, "探索完成")
