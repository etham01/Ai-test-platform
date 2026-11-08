from __future__ import annotations

from app.core.logging import redact_text


def test_redacts_api_key_and_password():
    text = redact_text("api_key=sk-super-secret-123 password=hunter2")
    assert "sk-super-secret-123" not in text
    assert "hunter2" not in text
    assert "<redacted>" in text


def test_redacts_bearer_and_database_url():
    text = redact_text(
        "Authorization: Bearer abc.def.ghi "
        "dsn=mysql+pymysql://smarttest:smarttest_dev_pw@127.0.0.1:3307/smarttest"
    )
    assert "abc.def.ghi" not in text
    assert "smarttest_dev_pw" not in text
    assert "Bearer <redacted>" in text
