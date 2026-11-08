#!/usr/bin/env python
"""End-to-end smoke test against a running SmartTest stack + DemoShop.

Requires: MySQL, Redis, FastAPI, Celery worker, and DemoShop running.
Run: .venv/Scripts/python.exe scripts/e2e_demo.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime

import httpx


def wait_task(client: httpx.Client, base: str, task_id: str, timeout: float = 180) -> dict:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = client.get(f"{base}/tasks/{task_id}").json()["data"]
        if last["status"] in {"succeeded", "failed", "cancelled"}:
            if last["status"] != "succeeded":
                raise RuntimeError(
                    f"task {task_id} {last['status']}: {last.get('message')} {last.get('error')}"
                )
            return last
        time.sleep(0.6)
    raise RuntimeError(f"task {task_id} did not finish: {last}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--demo-url", default="http://127.0.0.1:8001")
    parser.add_argument("--keep", action="store_true", help="keep the created project")
    args = parser.parse_args()
    base = args.api.rstrip("/")
    name = f"E2E-{datetime.now().strftime('%H%M%S')}"

    with httpx.Client(timeout=60) as client:
        print("[1/9] health")
        health = client.get("http://127.0.0.1:8000/health")
        require(health.status_code == 200, "API health failed")

        print("[2/9] create project")
        project = client.post(
            f"{base}/projects",
            json={
                "name": name,
                "description": "automated e2e smoke",
                "base_url": args.demo_url,
                "browser_type": "chrome",
                "scan_config": {"max_pages": 5, "max_depth": 1},
            },
        ).json()["data"]
        pid = project["id"]

        try:
            print("[3/9] configure Mock LLM")
            config = client.put(
                f"{base}/projects/{pid}/llm-config", json={"provider": "mock"}
            ).json()["data"]
            require(config["is_mock"] is True, "mock config not active")

            print("[4/9] explore DemoShop")
            task = client.post(
                f"{base}/projects/{pid}/pages/explore",
                json={
                    "max_pages": 5,
                    "max_depth": 1,
                    "timeout_seconds": 15,
                    "wait_after_load_ms": 200,
                },
            ).json()["data"]
            wait_task(client, base, task["task_id"])
            pages = client.get(f"{base}/projects/{pid}/pages?page_size=20").json()["data"]
            require(pages["total"] >= 3, "expected at least 3 pages")
            page_ids = [item["id"] for item in pages["items"][:3]]

            print("[5/9] create requirement")
            requirement = client.post(
                f"{base}/projects/{pid}/requirements",
                json={
                    "title": "E2E 登录与浏览",
                    "content": "验证首页、商品列表和登录页可访问；错误密码应提示错误。",
                    "related_page_ids": page_ids,
                },
            ).json()["data"]

            print("[6/9] analyze workflow")
            task = client.post(
                f"{base}/projects/{pid}/workflows/analyze",
                json={"requirement_id": requirement["id"], "page_ids": page_ids},
            ).json()["data"]
            wait_task(client, base, task["task_id"])
            workflows = client.get(f"{base}/projects/{pid}/workflows").json()["data"]
            require(workflows["total"] >= 1, "no workflows generated")

            print("[7/9] generate cases")
            task = client.post(
                f"{base}/projects/{pid}/ai/generate-cases",
                json={"requirement_id": requirement["id"], "max_cases": 3},
            ).json()["data"]
            wait_task(client, base, task["task_id"])
            cases = client.get(f"{base}/projects/{pid}/test-cases").json()["data"]
            require(cases["total"] >= 1, "no cases generated")

            print("[8/9] generate scripts")
            task = client.post(
                f"{base}/projects/{pid}/ai/generate-scripts",
                json={"test_case_ids": [cases["items"][0]["id"]]},
            ).json()["data"]
            wait_task(client, base, task["task_id"])
            scripts = client.get(f"{base}/projects/{pid}/test-scripts?page_size=20").json()["data"]
            validated = [item for item in scripts["items"] if item["status"] == "validated"]
            require(bool(validated), "no validated script generated")

            print("[9/9] execute + report")
            created = client.post(
                f"{base}/projects/{pid}/executions",
                json={"script_ids": [validated[0]["id"]], "timeout_seconds": 120, "mode": "local"},
            ).json()["data"]
            wait_task(client, base, created["task_id"], timeout=180)
            execution = client.get(f"{base}/executions/{created['execution_id']}").json()["data"]
            results = client.get(f"{base}/executions/{execution['id']}/results").json()["data"]
            require(execution["total"] >= 1, "execution produced no results")
            report = client.get("http://127.0.0.1:8000" + (execution["report_url"] or ""))
            require(report.status_code == 200 and len(report.content) > 1000, "report missing")

            summary = {
                "project_id": pid,
                "pages": pages["total"],
                "workflows": workflows["total"],
                "cases": cases["total"],
                "scripts": len(scripts["items"]),
                "validated_scripts": len(validated),
                "execution": {
                    "id": execution["id"],
                    "status": execution["status"],
                    "total": execution["total"],
                    "passed": execution["passed"],
                    "failed": execution["failed"],
                    "report_bytes": len(report.content),
                },
                "results": [
                    {"name": item["test_name"], "status": item["status"]}
                    for item in results["items"]
                ],
            }
            print("E2E SUMMARY")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        finally:
            if not args.keep:
                client.delete(f"{base}/projects/{pid}")
                print(f"(project {pid} soft-deleted; execution history retained)")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"E2E FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
