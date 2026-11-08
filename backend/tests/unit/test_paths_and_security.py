from __future__ import annotations

from pathlib import Path

import pytest
from app.core.paths import PathSecurityError, resolve_within, safe_filename
from app.core.security import decrypt_secret, encrypt_secret, mask_secret


def test_resolve_within_accepts_relative(tmp_path: Path):
    target = resolve_within(tmp_path, "projects/1/page.html")
    assert target == (tmp_path / "projects/1/page.html").resolve()


def test_resolve_within_rejects_traversal(tmp_path: Path):
    with pytest.raises(PathSecurityError):
        resolve_within(tmp_path, "../outside.txt")


def test_resolve_within_rejects_absolute(tmp_path: Path):
    with pytest.raises(PathSecurityError):
        resolve_within(tmp_path, str(tmp_path / "x.txt"))


def test_safe_filename_removes_directories_and_reserved_names():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("CON.py").startswith("_")
    assert "/" not in safe_filename("a/b/c.py")


def test_fernet_roundtrip_and_mask():
    token = encrypt_secret("sk-test-super-secret")
    assert token != "sk-test-super-secret"
    assert decrypt_secret(token) == "sk-test-super-secret"
    assert mask_secret("sk-test-super-secret") == "****cret"
    assert mask_secret(None) is None
