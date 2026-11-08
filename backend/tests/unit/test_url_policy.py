from __future__ import annotations

import pytest
from app.browser.url_policy import (
    URLPolicy,
    URLPolicyError,
    is_dangerous_link,
    normalize_url,
    origin_of,
    same_origin,
)


def test_normalize_url_dedupes_noise():
    assert normalize_url("HTTP://127.0.0.1:8001/products/#section") == (
        "http://127.0.0.1:8001/products"
    )
    assert normalize_url("http://127.0.0.1:8001/products/?utm_source=x&b=2&a=1") == (
        "http://127.0.0.1:8001/products?a=1&b=2"
    )
    assert normalize_url("/products/1", "http://127.0.0.1:8001/") == (
        "http://127.0.0.1:8001/products/1"
    )


def test_origin_and_same_origin():
    assert origin_of("http://127.0.0.1:8001/x") == "http://127.0.0.1:8001"
    assert origin_of("https://example.com:443/x") == "https://example.com"
    assert same_origin("http://127.0.0.1:8001/a", "http://127.0.0.1:8001/b")
    assert not same_origin("http://127.0.0.1:8001/a", "http://127.0.0.1:8002/a")


def test_dangerous_links_filtered():
    assert is_dangerous_link("mailto:a@b.com")
    assert is_dangerous_link("javascript:alert(1)")
    assert is_dangerous_link("/logout")
    assert is_dangerous_link("/files/report.pdf")
    assert not is_dangerous_link("/products/1")


def test_rejects_credentials_and_bad_schemes():
    with pytest.raises(URLPolicyError):
        normalize_url("file:///etc/passwd")
    with pytest.raises(URLPolicyError):
        normalize_url("http://user:pass@example.com/")


def test_dev_exact_origin_allows_demo_only():
    policy = URLPolicy.for_project(
        "http://127.0.0.1:8001",
        dev_allowed_origins=["http://127.0.0.1:8001"],
        resolve_dns=True,
    )
    assert policy.validate("http://127.0.0.1:8001/products")
    with pytest.raises(URLPolicyError):
        policy.validate("http://127.0.0.1:3306/")


def test_private_target_rejected_without_dev_exception():
    policy = URLPolicy.for_project(
        "http://127.0.0.1:8001",
        dev_allowed_origins=[],
        resolve_dns=True,
    )
    with pytest.raises(URLPolicyError):
        policy.validate("http://127.0.0.1:8001/")


def test_private_and_metadata_ip_rejected():
    private_policy = URLPolicy(
        base_url="http://192.168.1.10/",
        allowed_origins=["http://192.168.1.10"],
        dev_allowed_origins=[],
        resolve_dns=True,
    )
    with pytest.raises(URLPolicyError):
        private_policy.validate("http://192.168.1.10/")

    metadata_policy = URLPolicy(
        base_url="http://169.254.169.254/",
        allowed_origins=["http://169.254.169.254"],
        dev_allowed_origins=[],
        resolve_dns=True,
    )
    with pytest.raises(URLPolicyError):
        metadata_policy.validate("http://169.254.169.254/latest/meta-data/")


def test_resolve_link_filters_cross_origin():
    policy = URLPolicy.for_project(
        "http://127.0.0.1:8001",
        dev_allowed_origins=["http://127.0.0.1:8001"],
        resolve_dns=False,
    )
    assert policy.resolve_link("/products", "http://127.0.0.1:8001/") == (
        "http://127.0.0.1:8001/products"
    )
    assert policy.resolve_link("https://example.com/", "http://127.0.0.1:8001/") is None
    assert policy.resolve_link("/logout", "http://127.0.0.1:8001/") is None
