from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

from app.browser.site_explorer import (
    ExplorationCancelled,
    ExplorationTimeout,
    ExplorerConfig,
    SiteExplorer,
)
from app.browser.url_policy import URLPolicy
from app.models.enums import TaskStatus
from app.models.project import Project
from app.services.page_service import PageService
from app.tasks.celery_app import celery_app
from app.tasks.task_utils import (
    add_log,
    get_task,
    is_cancel_requested,
    mark_cancelled,
    mark_failed,
    mark_running,
    mark_succeeded,
    task_session,
    update_progress,
)

logger = logging.getLogger(__name__)


def _run_exploration(
    task_id: str,
    project_id: int,
    config: ExplorerConfig,
) -> None:
    with task_session() as db:
        task = get_task(db, task_id)
        if task is None:
            return

        try:
            project = db.get(Project, project_id)
            if project is None or project.deleted_at is not None:
                mark_failed(db, task, "项目不存在或已删除", "项目不可用")
                return

            config.start_url = urljoin(project.base_url, config.start_url or "")
            config.browser_type = project.browser_type or config.browser_type
            mark_running(db, task, "准备页面探索", 1)
            add_log(db, task, f"开始探索 {config.start_url}", "info")
            policy = URLPolicy.for_project(project.base_url)
            explorer = SiteExplorer(config, policy)

            page_map: dict[str, int] = {}
            pages_seen = 0

            def on_page(result) -> None:  # type: ignore[no-untyped-def]
                nonlocal pages_seen
                parent_id = page_map.get(result.discovered_from_url or "")
                page = PageService.upsert_page(
                    db,
                    project_id,
                    result,
                    discovered_from_page_id=parent_id,
                )
                if result.status == "parsed":
                    page_map[result.normalized_url] = page.id
                pages_seen += 1
                progress = min(99, int(pages_seen / max(1, config.max_pages) * 100))
                update_progress(
                    db,
                    task,
                    progress,
                    f"已处理 {pages_seen}/{config.max_pages} 个页面",
                )
                level = (
                    "info"
                    if result.status == "parsed"
                    else "warning"
                    if result.status == "blocked"
                    else "error"
                )
                suffix = f"；{result.error}" if result.error else ""
                add_log(
                    db,
                    task,
                    f"[{result.status}] {result.normalized_url}{suffix}",
                    level,
                )

            def on_progress(done: int, total: int, message: str) -> None:
                if task.status == TaskStatus.RUNNING.value:
                    update_progress(db, task, min(99, int(done / max(1, total) * 100)), message)

            def should_cancel() -> bool:
                return is_cancel_requested(db, task) or task.status == TaskStatus.CANCELLED.value

            explorer.explore(
                on_page=on_page,
                on_progress=on_progress,
                should_cancel=should_cancel,
            )
            PageService.resolve_relation_targets(db, project_id)

            if pages_seen == 0:
                mark_failed(db, task, "没有采集到任何页面", "采集失败")
                return

            fresh = get_task(db, task_id)
            if fresh is None:
                return
            page_count = PageService.count_pages(db, project_id)
            relation_count = PageService.count_relations(db, project_id)
            mark_succeeded(
                db,
                fresh,
                {
                    "pages": pages_seen,
                    "project_pages": page_count,
                    "relations": relation_count,
                    "start_url": config.start_url,
                },
                f"页面采集完成：{pages_seen} 个页面",
            )
            add_log(
                db,
                fresh,
                f"采集完成：{pages_seen} 个页面，{relation_count} 条关系",
                "info",
            )
        except ExplorationCancelled:
            db.rollback()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_cancelled(db, fresh, "页面探索已取消")
                add_log(db, fresh, "检测到取消请求，探索终止", "warning")
        except ExplorationTimeout as exc:
            db.rollback()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, str(exc), "页面探索超时")
                add_log(db, fresh, "页面探索超过总超时时间", "error")
        except Exception as exc:  # pragma: no cover - worker defensive path
            logger.exception("Page exploration failed")
            db.rollback()
            fresh = get_task(db, task_id)
            if fresh is not None:
                mark_failed(db, fresh, f"{type(exc).__name__}: {exc}", "页面探索失败")
                add_log(db, fresh, "页面探索发生异常，详见执行日志", "error")
            raise


@celery_app.task(bind=True, name="smarttest.pages.scan")
def scan_page_task(
    self,
    task_id: str,
    project_id: int,
    url: str | None = None,
    timeout_seconds: int = 15,
    wait_after_load_ms: int = 800,
) -> dict[str, Any]:
    _run_exploration(
        task_id,
        project_id,
        ExplorerConfig(
            start_url=url or "",
            max_pages=1,
            max_depth=0,
            page_timeout_seconds=timeout_seconds,
            total_timeout_seconds=max(60, timeout_seconds + 30),
            wait_after_load_ms=wait_after_load_ms,
        ),
    )
    return {"task_id": task_id}


@celery_app.task(bind=True, name="smarttest.pages.explore")
def explore_task(
    self,
    task_id: str,
    project_id: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    _run_exploration(
        task_id,
        project_id,
        ExplorerConfig(
            start_url=config.get("start_url") or "",
            max_pages=int(config.get("max_pages", 8)),
            max_depth=int(config.get("max_depth", 2)),
            page_timeout_seconds=int(config.get("timeout_seconds", 15)),
            total_timeout_seconds=int(config.get("total_timeout_seconds", 300)),
            wait_after_load_ms=int(config.get("wait_after_load_ms", 800)),
            browser_type=config.get("browser_type", "chromium"),
            extra_urls=list(config.get("extra_urls") or []),
        ),
    )
    return {"task_id": task_id}
