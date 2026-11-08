from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from app.browser.url_policy import origin_of
from app.core.config import settings
from app.core.paths import relative_posix, safe_filename
from app.core.time import utcnow
from app.execution.result_parser import parse_junit_xml
from app.models.project import Project
from app.models.test_script import TestScript

CONFTEST_TEMPLATE = '''\
import os
import pytest


ALLOWED_ORIGINS = [
    item for item in os.environ.get("SMARTTEST_ALLOWED_ORIGINS", "").split(",") if item
]


@pytest.fixture(autouse=True)
def smarttest_url_guard(context):
    def _handler(route):
        url = route.request.url
        if url.startswith(("data:", "about:", "blob:")) or any(
            url.startswith(origin) for origin in ALLOWED_ORIGINS
        ):
            route.continue_()
        else:
            route.abort()

    context.route("**/*", _handler)
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if page is None:
            return
        name = item.name.split("[")[0].replace("/", "_").replace("\\\\", "_")
        path = os.path.join(os.path.dirname(__file__), "screenshots", name + ".png")
        try:
            page.screenshot(path=path, full_page=True)
        except Exception:
            pass
'''

TEST_FUNC_RE = re.compile(r"^def\s+(test_[A-Za-z0-9_]+)\s*\(", re.MULTILINE)


@dataclass
class RunArtifacts:
    status: str
    results: list[dict[str, Any]] = field(default_factory=list)
    log_path: str | None = None
    report_path: str | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=utcnow)
    finished_at: datetime = field(default_factory=utcnow)


def _kill_tree(process: subprocess.Popen) -> None:
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.terminate()
        parent.terminate()
        _, alive = psutil.wait_procs(children + [parent], timeout=3)
        for item in alive:
            item.kill()
    except Exception:
        with contextlib.suppress(Exception):
            process.kill()


class LocalRunner:
    def __init__(self) -> None:
        self.workspace_root = settings.storage_root / "executions"

    def _write_workspace(
        self,
        execution_id: int,
        scripts: list[TestScript],
        project: Project,
    ) -> tuple[Path, list[str], dict[str, TestScript]]:
        workspace = self.workspace_root / str(execution_id)
        scripts_dir = workspace / "scripts"
        screenshots_dir = workspace / "screenshots"
        logs_dir = workspace / "logs"
        for directory in (scripts_dir, screenshots_dir, logs_dir):
            directory.mkdir(parents=True, exist_ok=True)

        filenames: list[str] = []
        function_map: dict[str, TestScript] = {}
        used_names: set[str] = set()
        for script in scripts:
            filename = safe_filename(script.filename, default=f"test_{script.id}.py")
            if not filename.endswith(".py"):
                filename += ".py"
            if filename in used_names:
                filename = f"{Path(filename).stem}_{script.id}.py"
            used_names.add(filename)
            (scripts_dir / filename).write_text(script.content, encoding="utf-8")
            filenames.append(f"scripts/{filename}")
            for match in TEST_FUNC_RE.finditer(script.content):
                function_map.setdefault(match.group(1), script)

        (workspace / "conftest.py").write_text(CONFTEST_TEMPLATE, encoding="utf-8")
        (workspace / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        return workspace, filenames, function_map

    def run(
        self,
        *,
        execution_id: int,
        scripts: list[TestScript],
        project: Project,
        timeout_seconds: int,
        should_cancel: Callable[[], bool],
    ) -> RunArtifacts:
        workspace, filenames, function_map = self._write_workspace(
            execution_id, scripts, project
        )
        started = utcnow()
        log_path = workspace / "logs" / "run.log"
        report_path = workspace / "report.html"
        results_path = workspace / "results.xml"
        allowed_origin = origin_of(project.base_url)

        command = [
            sys.executable,
            "-m",
            "pytest",
            *filenames,
            "--junitxml=results.xml",
            "--html=report.html",
            "--self-contained-html",
            "-q",
            "-p",
            "no:cacheprovider",
        ]
        channel = settings.browser_channel
        if project.browser_type in {"chrome", "msedge"}:
            channel = project.browser_type
        if channel:
            command.extend(["--browser-channel", channel])

        safe_keys = {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "PATHEXT",
            "COMSPEC",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "PROGRAMFILES",
            "PROGRAMFILES(X86)",
            "PLAYWRIGHT_BROWSERS_PATH",
        }
        env = {key: value for key, value in os.environ.items() if key in safe_keys}
        env["PYTHONIOENCODING"] = "utf-8"
        env["SMARTTEST_ALLOWED_ORIGINS"] = allowed_origin

        timed_out = False
        cancelled = False
        error: str | None = None
        with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
            process = subprocess.Popen(
                command,
                cwd=workspace,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                ),
            )
            deadline = time.monotonic() + max(5, timeout_seconds)
            while process.poll() is None:
                if should_cancel():
                    cancelled = True
                    _kill_tree(process)
                    break
                if time.monotonic() > deadline:
                    timed_out = True
                    _kill_tree(process)
                    break
                time.sleep(0.5)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _kill_tree(process)
                process.wait(timeout=5)

        try:
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            if len(log_text) > 2_000_000:
                log_path.write_text(log_text[:2_000_000], encoding="utf-8")
        except OSError:
            pass

        raw_results = parse_junit_xml(results_path)
        for result in raw_results:
            base_name = result["name"].split("[")[0]
            screenshot = workspace / "screenshots" / f"{base_name}.png"
            result["script"] = function_map.get(base_name)
            result["screenshot_path"] = (
                relative_posix(screenshot) if screenshot.is_file() else None
            )

        if cancelled:
            status = "cancelled"
        elif timed_out:
            status = "timeout"
        elif not raw_results:
            status = "error"
            error = "pytest 未产生测试结果（可能是收集/启动失败），请查看执行日志"
        elif any(item["status"] in {"failed", "error"} for item in raw_results):
            status = "failed"
        else:
            status = "passed"

        finished = utcnow()
        return RunArtifacts(
            status=status,
            results=raw_results,
            log_path=relative_posix(log_path) if log_path.is_file() else None,
            report_path=relative_posix(report_path) if report_path.is_file() else None,
            error=error,
            started_at=started,
            finished_at=finished,
        )
