from __future__ import annotations

from app.execution.script_validator import validate_script

VALID_SCRIPT = '''
import pytest
from playwright.sync_api import Page, expect

def test_home(page: Page):
    page.goto("http://127.0.0.1:8001/")
    expect(page).to_have_title("DemoShop")
'''


def test_valid_script_passes():
    report = validate_script(VALID_SCRIPT)
    assert report["ok"] is True
    assert report["issues"] == []


def test_dangerous_import_rejected():
    report = validate_script(
        "import os\nfrom playwright.sync_api import expect\n"
        "def test_x(page):\n    expect(page).to_have_title('x')\n"
    )
    assert report["ok"] is False
    assert any(issue["code"] == "IMPORT_DENIED" for issue in report["issues"])


def test_eval_rejected():
    report = validate_script(
        "from playwright.sync_api import expect\n"
        "def test_x(page):\n    eval('1 + 1')\n    expect(page).to_have_title('x')\n"
    )
    assert report["ok"] is False
    assert any(issue["code"] == "NAME_DENIED" for issue in report["issues"])


def test_missing_assertion_rejected():
    report = validate_script(
        "from playwright.sync_api import Page\n"
        "def test_x(page: Page):\n    page.goto('http://127.0.0.1:8001/')\n"
    )
    assert report["ok"] is False
    assert any(issue["code"] == "NO_ASSERTION" for issue in report["issues"])


def test_syntax_error_rejected():
    report = validate_script("def test_x(:\n    pass\n")
    assert report["ok"] is False
    assert any(issue["code"] == "SYNTAX_ERROR" for issue in report["issues"])


def test_while_true_only_warns():
    report = validate_script(
        "from playwright.sync_api import expect\n"
        "def test_x(page):\n"
        "    while True:\n"
        "        break\n"
        "    expect(page).to_have_title('x')\n"
    )
    assert report["ok"] is True
    assert any(issue["code"] == "WHILE_TRUE" for issue in report["issues"])
