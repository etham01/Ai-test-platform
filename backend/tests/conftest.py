from __future__ import annotations

import os

# Must be set before importing app.config / app.db.session.
TEST_DATABASE_URL = (
    "mysql+pymysql://smarttest:smarttest_dev_pw@127.0.0.1:3307/smarttest_test"
    "?charset=utf8mb4"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

import pytest  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.add_all(
            [
                User(id=1, username="demo", display_name="演示用户", is_active=True),
                User(id=2, username="other", display_name="其他用户", is_active=True),
            ]
        )
        db.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    with SessionLocal() as db:
        yield db
