from __future__ import annotations

import pytest
from app.schemas.project import ProjectCreate, ProjectUpdate
from pydantic import ValidationError


def test_project_create_requires_http_url():
    with pytest.raises(ValidationError):
        ProjectCreate(name="x", base_url="file:///tmp/a")
    with pytest.raises(ValidationError):
        ProjectCreate(name="x", base_url="http://user:pass@example.com")


def test_project_create_accepts_local_demo():
    project = ProjectCreate(name=" Demo ", base_url="http://127.0.0.1:8001")
    assert project.name == "Demo"
    assert project.browser_type == "chromium"


def test_project_update_optional_fields():
    update = ProjectUpdate(description=None)
    assert update.model_dump(exclude_unset=True) == {"description": None}
