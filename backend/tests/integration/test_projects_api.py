from __future__ import annotations

import pytest
from app.models.project import Project
from app.models.user import User

pytestmark = pytest.mark.integration


def _project_payload(name: str = "DemoShop") -> dict:
    return {
        "name": name,
        "description": "local demo",
        "base_url": "http://127.0.0.1:8001",
        "browser_type": "chromium",
        "scan_config": {"max_pages": 8, "max_depth": 2},
    }


def test_health_and_request_id(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"].startswith("req_")

    deps = client.get("/api/v1/health/deps")
    assert deps.status_code == 200
    body = deps.json()
    assert body["success"] is True
    assert body["data"]["database"]["ok"] is True
    assert body["data"]["redis"]["ok"] is True


def test_project_crud_and_persistence(client):
    created = client.post("/api/v1/projects", json=_project_payload())
    assert created.status_code == 201
    body = created.json()
    assert body["success"] is True
    project = body["data"]
    project_id = project["id"]
    assert project["name"] == "DemoShop"
    assert project["owner_id"] == 1
    assert project["scan_config"]["max_pages"] == 8

    listed = client.get("/api/v1/projects")
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] >= 1

    fetched = client.get(f"/api/v1/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["id"] == project_id

    updated = client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "DemoShop 2", "description": "updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "DemoShop 2"

    deleted = client.delete(f"/api/v1/projects/{project_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/projects/{project_id}").status_code == 404
    assert client.get("/api/v1/projects").json()["data"]["total"] == 0


def test_project_isolation_returns_404(client, db_session):
    other = db_session.get(User, 2)
    assert other is not None
    project = Project(
        owner_id=other.id,
        name="Other project",
        base_url="http://127.0.0.1:8001",
        browser_type="chromium",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    response = client.get(f"/api/v1/projects/{project.id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert client.get("/api/v1/projects").json()["data"]["total"] == 0


def test_project_validation(client):
    bad = client.post(
        "/api/v1/projects",
        json={
            "name": "Bad",
            "base_url": "file:///etc/passwd",
            "browser_type": "chromium",
        },
    )
    assert bad.status_code == 422
    assert bad.json()["success"] is False
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"


def test_debug_task_runs_in_eager_mode(client):
    created = client.post(
        "/api/v1/tasks/debug",
        json={"message": "eager-ok", "sleep_seconds": 0},
    )
    assert created.status_code == 202
    task_id = created.json()["data"]["task_id"]

    task = client.get(f"/api/v1/tasks/{task_id}")
    assert task.status_code == 200
    payload = task.json()["data"]
    assert payload["status"] == "succeeded"
    assert payload["progress"] == 100
    assert payload["result"]["message"] == "eager-ok"

    logs = client.get(f"/api/v1/tasks/{task_id}/logs")
    assert logs.status_code == 200
    assert logs.json()["data"]["total"] >= 2
