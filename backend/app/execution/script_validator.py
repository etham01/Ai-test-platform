from __future__ import annotations

import ast
from datetime import UTC, datetime
from typing import Any

VALIDATOR_VERSION = "v1"
MAX_SCRIPT_BYTES = 60_000

ALLOWED_MODULES = {
    "__future__",
    "pytest",
    "playwright.sync_api",
    "re",
    "json",
    "time",
    "math",
    "typing",
    "datetime",
}
DENIED_NAMES = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "exit",
    "getattr",
    "globals",
    "hasattr",
    "help",
    "input",
    "locals",
    "open",
    "quit",
    "setattr",
    "vars",
}
DENIED_METHODS = {
    "execv",
    "fork",
    "popen",
    "remove",
    "rmdir",
    "spawn",
    "system",
    "unlink",
}


def _issue(
    issues: list[dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    line: int | None = None,
    col: int | None = None,
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "line": line,
            "col": col,
        }
    )


def _module_allowed(module: str | None) -> bool:
    if not module:
        return False
    return module in ALLOWED_MODULES


def validate_script(content: str, *, filename: str | None = None) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    encoded_size = len(content.encode("utf-8"))
    if not content.strip():
        _issue(issues, "error", "EMPTY_SCRIPT", "脚本内容为空")
    if encoded_size > MAX_SCRIPT_BYTES:
        _issue(
            issues,
            "error",
            "SCRIPT_TOO_LARGE",
            f"脚本超过 {MAX_SCRIPT_BYTES} 字节上限",
        )

    tree: ast.Module | None = None
    if content.strip():
        try:
            tree = ast.parse(content, filename=filename or "<generated.py>")
        except SyntaxError as exc:
            _issue(
                issues,
                "error",
                "SYNTAX_ERROR",
                f"Python 语法错误: {exc.msg}",
                exc.lineno,
                exc.offset,
            )

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not _module_allowed(alias.name):
                        _issue(
                            issues,
                            "error",
                            "IMPORT_DENIED",
                            f"不允许导入模块: {alias.name}",
                            node.lineno,
                            node.col_offset,
                        )
            elif isinstance(node, ast.ImportFrom):
                if not _module_allowed(node.module):
                    _issue(
                        issues,
                        "error",
                        "IMPORT_DENIED",
                        f"不允许从模块导入: {node.module}",
                        node.lineno,
                        node.col_offset,
                    )
            elif isinstance(node, ast.Attribute):
                if node.attr.startswith("__"):
                    _issue(
                        issues,
                        "error",
                        "DUNDER_ATTRIBUTE",
                        f"不允许访问双下划线属性: {node.attr}",
                        node.lineno,
                        node.col_offset,
                    )
                elif node.attr in DENIED_METHODS:
                    _issue(
                        issues,
                        "error",
                        "METHOD_DENIED",
                        f"不允许调用危险方法: {node.attr}",
                        node.lineno,
                        node.col_offset,
                    )
            elif isinstance(node, ast.Name):
                if node.id in DENIED_NAMES:
                    _issue(
                        issues,
                        "error",
                        "NAME_DENIED",
                        f"不允许使用名称: {node.id}",
                        node.lineno,
                        node.col_offset,
                    )
                elif node.id.startswith("__"):
                    _issue(
                        issues,
                        "error",
                        "DUNDER_NAME",
                        f"不允许使用双下划线名称: {node.id}",
                        node.lineno,
                        node.col_offset,
                    )
            elif (
                isinstance(node, ast.While)
                and isinstance(node.test, ast.Constant)
                and node.test.value is True
            ):
                _issue(
                    issues,
                    "warning",
                    "WHILE_TRUE",
                    "存在 while True，请确认有退出条件；执行器超时会兜底",
                    node.lineno,
                    node.col_offset,
                )

        test_functions = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ]
        if not test_functions:
            _issue(issues, "error", "NO_TEST_FUNCTION", "脚本中缺少 def test_ 测试函数")

        has_assert = any(isinstance(node, ast.Assert) for node in ast.walk(tree))
        has_expect = any(
            isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "expect")
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "expect"
                )
            )
            for node in ast.walk(tree)
        )
        if not has_assert and not has_expect:
            _issue(issues, "error", "NO_ASSERTION", "脚本中缺少断言或 expect(...)")

    errors = [item for item in issues if item["severity"] == "error"]
    return {
        "ok": not errors,
        "issues": issues,
        "checked_at": datetime.now(UTC).isoformat(),
        "validator_version": VALIDATOR_VERSION,
        "size_bytes": encoded_size,
    }
