from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import urlsplit

from app.ai.providers.base import LLMError, LLMResult

_PRODUCT_PATH = re.compile(r"/products/\d+/?$")


def _path(page: dict[str, Any]) -> str:
    return urlsplit(str(page.get("url", ""))).path or "/"


def _find_page(pages: list[dict[str, Any]], *needles: str) -> dict[str, Any] | None:
    # Prefer an exact path match, so /products wins over /products/4.
    exact_paths = {
        needle.rstrip("/")
        for needle in needles
        if needle.startswith("/")
    }
    for page in pages:
        if _path(page).rstrip("/") in exact_paths:
            return page
    for page in pages:
        haystack = f"{page.get('url', '')} {page.get('title', '')}".lower()
        if any(needle.lower() in haystack for needle in needles):
            return page
    return None


def _element_text(element: dict[str, Any]) -> str:
    return " ".join(
        str(element.get(key) or "")
        for key in ("accessible_name", "label", "placeholder", "text")
    ).strip()


def _label(
    page: dict[str, Any] | None,
    *needles: str,
    types: set[str] | None = None,
) -> str | None:
    if not page:
        return None
    for element in page.get("elements", []) or []:
        if types and element.get("element_type") not in types and element.get("tag") not in types:
            continue
        haystack = _element_text(element)
        if any(needle in haystack for needle in needles):
            return (
                element.get("accessible_name")
                or element.get("label")
                or element.get("placeholder")
                or element.get("text")
                or needles[0]
            )
    return None


def _page_id(page: dict[str, Any] | None) -> int | None:
    return int(page["id"]) if page and page.get("id") is not None else None


def _page_ref(page: dict[str, Any] | None) -> str | None:
    page_id = _page_id(page)
    return str(page_id) if page_id is not None else None


def _path_of(page: dict[str, Any] | None, default: str = "/") -> str:
    return _path(page) if page else default


def _py(value: Any) -> str:
    return json.dumps(str(value) if value is not None else "", ensure_ascii=False)


def _unique_ids(pages: list[dict[str, Any] | None]) -> list[int]:
    result: list[int] = []
    for page in pages:
        page_id = _page_id(page)
        if page_id is not None and page_id not in result:
            result.append(page_id)
    return result


class MockLLMProvider:
    provider_name = "mock"
    model = "mock-v1"
    is_mock = True

    def generate(
        self,
        task: str,
        payload: dict[str, Any],
        *,
        prompt_version: str = "v1",
        repair_note: str | None = None,
    ) -> LLMResult:
        started = time.perf_counter()
        if task == "workflow_analysis":
            data = {"workflows": self._workflows(payload)}
        elif task == "case_generation":
            data = {"cases": self._cases(payload)}
        elif task == "script_generation":
            data = self._script(payload)
        elif task == "failure_analysis":
            data = self._failure(payload)
        else:
            raise LLMError(
                "MOCK_UNSUPPORTED",
                f"Mock provider 暂不支持任务: {task}",
            )
        return LLMResult(
            content=json.dumps(data, ensure_ascii=False),
            provider=self.provider_name,
            model=self.model,
            is_mock=True,
            prompt_version=prompt_version,
            duration_ms=round((time.perf_counter() - started) * 1000),
            raw={"mock": True, "task": task},
        )

    def _workflows(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        pages = payload.get("pages", []) or []
        if not pages:
            return []
        home = next((p for p in pages if _path(p) == "/"), None) or pages[0]
        products = _find_page(pages, "/products", "商品列表")
        detail = next(
            (p for p in pages if _PRODUCT_PATH.search(_path(p))), None
        )
        cart = _find_page(pages, "/cart", "购物车")
        login = _find_page(pages, "/login", "登录")

        workflows: list[dict[str, Any]] = []
        steps: list[dict[str, Any]] = []

        def add_step(
            page: dict[str, Any] | None,
            action: str,
            target: str,
            description: str,
            value: str | None = None,
        ) -> None:
            steps.append(
                {
                    "step_no": len(steps) + 1,
                    "page_id": _page_id(page),
                    "action": action,
                    "target": target,
                    "value": value,
                    "description": description,
                }
            )

        add_step(home, "goto", _path_of(home), "打开首页")
        if products:
            add_step(
                products,
                "click",
                _label(home, "商品列表", "商品") or "商品列表",
                "从首页进入商品列表",
            )
        if detail:
            add_step(
                detail,
                "click",
                _label(products, "查看详情", "详情") or "查看详情",
                "打开商品详情",
            )
        if cart:
            add_step(
                cart,
                "click",
                _label(products or detail, "购物车") or "购物车",
                "进入购物车",
            )
        add_step(
            cart or detail or home,
            "assert",
            "页面标题",
            "确认当前页面可访问",
            (cart or detail or home).get("title"),
        )
        workflows.append(
            {
                "name": "浏览商品并进入购物车",
                "description": "从首页进入商品列表、打开详情并进入购物车。",
                "steps": steps,
                "involved_page_ids": _unique_ids([home, products, detail, cart]),
                "uncertainty": "未提交表单；加入购物车与结算行为需要执行脚本确认。",
                "confidence": 0.55,
            }
        )

        if login and products:
            login_steps: list[dict[str, Any]] = []
            login_steps.append(
                {
                    "step_no": 1,
                    "page_id": _page_id(login),
                    "action": "goto",
                    "target": _path_of(login),
                    "value": None,
                    "description": "打开登录页",
                }
            )
            login_steps.append(
                {
                    "step_no": 2,
                    "page_id": _page_id(login),
                    "action": "fill",
                    "target": _label(login, "用户名", "账号", types={"input"}) or "用户名",
                    "value": "demo",
                    "description": "输入演示用户名",
                }
            )
            login_steps.append(
                {
                    "step_no": 3,
                    "page_id": _page_id(login),
                    "action": "fill",
                    "target": _label(login, "密码", types={"input"}) or "密码",
                    "value": "demo123",
                    "description": "输入演示密码",
                }
            )
            login_steps.append(
                {
                    "step_no": 4,
                    "page_id": _page_id(login),
                    "action": "click",
                    "target": _label(login, "登录", "提交", types={"button"}) or "登录",
                    "value": None,
                    "description": "提交登录表单",
                }
            )
            login_steps.append(
                {
                    "step_no": 5,
                    "page_id": _page_id(products),
                    "action": "assert",
                    "target": "页面标题",
                    "value": products.get("title"),
                    "description": "确认登录后进入商品列表",
                }
            )
            workflows.append(
                {
                    "name": "登录后浏览商品",
                    "description": "使用演示账号登录并进入商品列表。",
                    "steps": login_steps,
                    "involved_page_ids": _unique_ids([login, products]),
                    "uncertainty": "登录成功后的跳转由已采集链接推断，需人工确认登录凭据。",
                    "confidence": 0.6,
                }
            )
        return workflows

    def _cases(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        pages = payload.get("pages", []) or []
        if not pages:
            return []
        max_cases = int(payload.get("max_cases", 5))
        home = next((p for p in pages if _path(p) == "/"), None) or pages[0]
        products = _find_page(pages, "/products", "商品列表")
        detail = next(
            (p for p in pages if _PRODUCT_PATH.search(_path(p))), None
        )
        cart = _find_page(pages, "/cart", "购物车")
        login = _find_page(pages, "/login", "登录")

        cases: list[dict[str, Any]] = []
        preconditions = ["本地 DemoShop 站点已启动"]

        def add_case(case: dict[str, Any]) -> None:
            case["case_code"] = f"TC-{len(cases) + 1:03d}"
            cases.append(case)

        home_title = home.get("title") or "首页"
        add_case(
            {
                "title": "首页可访问",
                "module": "冒烟",
                "priority": "P0",
                "preconditions": preconditions,
                "related_page_ids": _unique_ids([home]),
                "steps": [
                    {
                        "step_no": 1,
                        "page_reference": _page_ref(home),
                        "action": "goto",
                        "target": _path_of(home),
                        "value": None,
                        "description": "打开首页",
                    },
                    {
                        "step_no": 2,
                        "page_reference": _page_ref(home),
                        "action": "assert",
                        "target": "页面标题",
                        "value": home_title,
                        "description": "确认首页标题",
                    },
                ],
                "test_data": {},
                "expected_result": f"首页可访问，标题为“{home_title}”",
                "assertions": [
                    {
                        "assertion_type": "title",
                        "target": "页面标题",
                        "expected": home_title,
                        "source": "observed_page",
                        "confidence": 1.0,
                    }
                ],
                "assumptions": [],
            }
        )

        if products and len(cases) < max_cases:
            products_title = products.get("title") or "商品列表"
            add_case(
                {
                    "title": "商品列表可访问",
                    "module": "商品浏览",
                    "priority": "P1",
                    "preconditions": preconditions,
                    "related_page_ids": _unique_ids([products]),
                    "steps": [
                        {
                            "step_no": 1,
                            "page_reference": _page_ref(products),
                            "action": "goto",
                            "target": _path_of(products),
                            "value": None,
                            "description": "打开商品列表",
                        },
                        {
                            "step_no": 2,
                            "page_reference": _page_ref(products),
                            "action": "assert",
                            "target": "页面标题",
                            "value": products_title,
                            "description": "确认商品列表标题",
                        },
                    ],
                    "test_data": {},
                    "expected_result": f"商品列表可访问，标题为“{products_title}”",
                    "assertions": [
                        {
                            "assertion_type": "title",
                            "target": "页面标题",
                            "expected": products_title,
                            "source": "observed_page",
                            "confidence": 1.0,
                        }
                    ],
                    "assumptions": [],
                }
            )

        if login and products and len(cases) < max_cases:
            username_target = _label(
                login, "用户名", "账号", types={"input"}
            ) or "用户名"
            password_target = _label(login, "密码", types={"input"}) or "密码"
            submit_target = _label(
                login, "登录", "提交", types={"button"}
            ) or "登录"
            add_case(
                {
                    "title": "正确密码登录成功",
                    "module": "认证",
                    "priority": "P0",
                    "preconditions": preconditions + ["已打开登录页"],
                    "related_page_ids": _unique_ids([login, products]),
                    "steps": [
                        {
                            "step_no": 1,
                            "page_reference": _page_ref(login),
                            "action": "goto",
                            "target": _path_of(login),
                            "value": None,
                            "description": "打开登录页",
                        },
                        {
                            "step_no": 2,
                            "page_reference": _page_ref(login),
                            "action": "fill",
                            "target": username_target,
                            "value": "demo",
                            "description": "输入用户名",
                        },
                        {
                            "step_no": 3,
                            "page_reference": _page_ref(login),
                            "action": "fill",
                            "target": password_target,
                            "value": "demo123",
                            "description": "输入密码",
                        },
                        {
                            "step_no": 4,
                            "page_reference": _page_ref(login),
                            "action": "click",
                            "target": submit_target,
                            "value": None,
                            "description": "提交登录",
                        },
                        {
                            "step_no": 5,
                            "page_reference": _page_ref(products),
                            "action": "assert",
                            "target": "current_url",
                            "value": "/products",
                            "description": "确认跳转到商品列表",
                        },
                    ],
                    "test_data": {"username": "demo", "password": "demo123"},
                    "expected_result": "登录成功并跳转到商品列表",
                    "assertions": [
                        {
                            "assertion_type": "url",
                            "target": "current_url",
                            "expected": "/products",
                            "source": "model_inference",
                            "confidence": 0.7,
                        }
                    ],
                    "assumptions": [
                        "登录成功后的跳转由页面链接和本地演示站点行为推断，需人工确认。"
                    ],
                }
            )

        if login and len(cases) < max_cases:
            username_target = _label(
                login, "用户名", "账号", types={"input"}
            ) or "用户名"
            password_target = _label(login, "密码", types={"input"}) or "密码"
            submit_target = _label(
                login, "登录", "提交", types={"button"}
            ) or "登录"
            add_case(
                {
                    "title": "错误密码登录失败",
                    "module": "认证",
                    "priority": "P1",
                    "preconditions": preconditions + ["已打开登录页"],
                    "related_page_ids": _unique_ids([login]),
                    "steps": [
                        {
                            "step_no": 1,
                            "page_reference": _page_ref(login),
                            "action": "goto",
                            "target": _path_of(login),
                            "value": None,
                            "description": "打开登录页",
                        },
                        {
                            "step_no": 2,
                            "page_reference": _page_ref(login),
                            "action": "fill",
                            "target": username_target,
                            "value": "demo",
                            "description": "输入用户名",
                        },
                        {
                            "step_no": 3,
                            "page_reference": _page_ref(login),
                            "action": "fill",
                            "target": password_target,
                            "value": "wrong-password",
                            "description": "输入错误密码",
                        },
                        {
                            "step_no": 4,
                            "page_reference": _page_ref(login),
                            "action": "click",
                            "target": submit_target,
                            "value": None,
                            "description": "提交登录",
                        },
                        {
                            "step_no": 5,
                            "page_reference": _page_ref(login),
                            "action": "assert",
                            "target": "页面文本",
                            "value": "用户名或密码不正确",
                            "description": "确认出现错误提示",
                        },
                    ],
                    "test_data": {"username": "demo", "password": "wrong-password"},
                    "expected_result": "页面显示登录失败提示",
                    "assertions": [
                        {
                            "assertion_type": "text",
                            "target": "页面文本",
                            "expected": "用户名或密码不正确",
                            "source": "model_inference",
                            "confidence": 0.6,
                        }
                    ],
                    "assumptions": [
                        "错误提示文案来自本地演示站点的预期行为，需人工确认。"
                    ],
                }
            )

        if detail and cart and len(cases) < max_cases:
            product_name = (detail.get("title") or "商品").split(" · ")[0]
            add_target = _label(
                detail, "加入购物车", types={"button"}
            ) or "加入购物车"
            add_case(
                {
                    "title": f"加入购物车：{product_name}",
                    "module": "购物车",
                    "priority": "P1",
                    "preconditions": preconditions,
                    "related_page_ids": _unique_ids([detail, cart]),
                    "steps": [
                        {
                            "step_no": 1,
                            "page_reference": _page_ref(detail),
                            "action": "goto",
                            "target": _path_of(detail),
                            "value": None,
                            "description": "打开商品详情",
                        },
                        {
                            "step_no": 2,
                            "page_reference": _page_ref(detail),
                            "action": "click",
                            "target": add_target,
                            "value": None,
                            "description": "点击加入购物车",
                        },
                        {
                            "step_no": 3,
                            "page_reference": _page_ref(cart),
                            "action": "assert",
                            "target": "页面文本",
                            "value": product_name,
                            "description": "确认购物车包含该商品",
                        },
                    ],
                    "test_data": {},
                    "expected_result": "购物车页面显示所选商品",
                    "assertions": [
                        {
                            "assertion_type": "url",
                            "target": "current_url",
                            "expected": "/cart",
                            "source": "observed_page",
                            "confidence": 0.8,
                        },
                        {
                            "assertion_type": "text",
                            "target": "页面文本",
                            "expected": product_name,
                            "source": "observed_page",
                            "confidence": 0.7,
                        },
                    ],
                    "assumptions": [
                        "加入购物车后的页面跳转来自已观察到的表单动作，需执行确认。"
                    ],
                }
            )

        return cases[:max_cases]

    def _script(self, payload: dict[str, Any]) -> dict[str, Any]:
        case = payload.get("case") or {}
        project = payload.get("project") or {}
        base_url = str(project.get("base_url") or "http://127.0.0.1:8001").rstrip("/")
        case_code = str(case.get("case_code") or "TC-001")
        safe_code = re.sub(r"[^a-z0-9_]+", "_", case_code.lower()).strip("_") or "case"
        test_name = f"test_{safe_code}"
        steps = case.get("steps") or []
        assertions = case.get("assertions") or []

        lines = [
            "import re",
            "import pytest",
            "from playwright.sync_api import Page, expect",
            "",
            f"BASE_URL = {_py(base_url)}",
            "",
            f"# smarttest: case_code={case_code} case_id={case.get('id')}",
            f"def {test_name}(page: Page):",
        ]

        def add_step(step: dict[str, Any]) -> None:
            action = step.get("action")
            target = step.get("target") or ""
            value = step.get("value")
            if action == "goto":
                path = target if target.startswith("/") else f"/{target}"
                lines.append(f"    page.goto(BASE_URL + {_py(path)})")
            elif action == "fill":
                lines.append(
                    f"    page.get_by_label({_py(target)}).fill({_py(value or '')})"
                )
            elif action == "click":
                types: set[str] = set()
                for page in payload.get("pages", []) or []:
                    for element in page.get("elements", []) or []:
                        if (
                            target
                            in {
                                element.get("accessible_name"),
                                element.get("label"),
                                element.get("text"),
                                element.get("placeholder"),
                            }
                            and element.get("element_type")
                        ):
                            types.add(str(element["element_type"]))
                if "button" in types:
                    lines.append(
                        f"    page.get_by_role(\"button\", name={_py(target)}, exact=True).click()"
                    )
                elif "link" in types:
                    lines.append(
                        "    page.get_by_role(\"link\", name="
                        f"{_py(target)}, exact=True).first.click()"
                    )
                else:
                    lines.append(
                        f"    page.get_by_text({_py(target)}, exact=True).first.click()"
                    )
                lines.append('    page.wait_for_load_state("domcontentloaded")')
            elif action == "select":
                lines.append(
                    f"    page.get_by_label({_py(target)}).select_option({_py(value or '')})"
                )
            elif action == "check":
                lines.append(f"    page.get_by_label({_py(target)}).check()")
            elif action == "uncheck":
                lines.append(f"    page.get_by_label({_py(target)}).uncheck()")
            elif action == "press":
                lines.append(
                    f"    page.get_by_label({_py(target)}).press({_py(value or 'Enter')})"
                )
            elif action == "wait":
                try:
                    milliseconds = int(value or 500)
                except (TypeError, ValueError):
                    milliseconds = 500
                lines.append(f"    page.wait_for_timeout({milliseconds})")
            elif action == "assert":
                if target in {"页面标题", "title"}:
                    assertion_type = "title"
                elif target in {"current_url", "url"}:
                    assertion_type = "url"
                elif target in {"页面文本", "text"}:
                    assertion_type = "text"
                else:
                    assertion_type = "element_visible"
                lines.append(
                    "    " + self._assertion_line(assertion_type, target, value)
                )
            elif action == "custom":
                lines.append(f"    # custom step: {target}")

        for step in steps:
            if isinstance(step, dict):
                add_step(step)

        if not steps:
            lines.append('    page.goto(BASE_URL + "/")')

        for assertion in assertions:
            if not isinstance(assertion, dict):
                continue
            line = self._assertion_line(
                str(assertion.get("assertion_type") or "text"),
                str(assertion.get("target") or ""),
                assertion.get("expected"),
            )
            lines.append("    " + line)

        if not assertions:
            lines.append('    expect(page).to_have_url(re.compile(".*"))')

        lines.extend(
            [
                "",
                "# Mock 生成：只覆盖已采集页面和演示数据，执行前请人工复核。",
            ]
        )
        return {
            "filename": f"{safe_code}.py",
            "content": chr(10).join(lines) + chr(10),
            "notes": "Mock 模板根据结构化用例生成；仅用于流程演示。",
            "assumptions": list(case.get("assumptions") or [])
            + ["Mock 脚本由固定模板生成，定位器稳定性需执行确认。"],
        }

    def _assertion_line(self, assertion_type: str, target: str, expected: Any) -> str:
        if assertion_type == "url":
            return f"expect(page).to_have_url(re.compile(re.escape({_py(expected)})))"
        if assertion_type == "title":
            return f"expect(page).to_have_title({_py(expected)})"
        if assertion_type == "text":
            return f"expect(page.locator(\"body\")).to_contain_text({_py(expected)})"
        if assertion_type == "element_text":
            return (
                f"expect(page.get_by_text({_py(target)}, exact=False))"
                f".to_contain_text({_py(expected)})"
            )
        if assertion_type == "value":
            return (
                f"expect(page.get_by_label({_py(target)}))"
                f".to_have_value({_py(expected)})"
            )
        if assertion_type == "count":
            try:
                count = int(expected)
            except (TypeError, ValueError):
                count = 1
            return (
                f"expect(page.get_by_text({_py(target)}, exact=False))"
                f".to_have_count({count})"
            )
        if assertion_type == "custom":
            return f"# custom assertion: {target} -> {expected}"
        return (
            f"expect(page.get_by_text({_py(target)}, exact=False)).to_be_visible()"
        )

    def _failure(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = payload.get("result") or {}
        message = str(result.get("failure_message") or "").strip()
        traceback_text = str(result.get("traceback") or "").strip()
        observed = message or traceback_text[:1200] or "测试失败，但未提供详细错误信息"
        haystack = (message + chr(10) + traceback_text).lower()
        causes: list[dict[str, Any]] = []
        if "page title expected to be" in haystack or "to_have_title" in haystack:
            causes.append(
                {
                    "cause": "脚本断言中的预期标题与实际页面标题不一致",
                    "evidence": observed[:1200],
                    "confidence": 0.85,
                }
            )
        elif "timeout" in haystack:
            causes.append(
                {
                    "cause": "元素或页面在超时时间内未出现",
                    "evidence": observed[:1200],
                    "confidence": 0.7,
                }
            )
        elif "strict mode violation" in haystack:
            causes.append(
                {
                    "cause": "定位器匹配到多个元素，触发严格模式冲突",
                    "evidence": observed[:1200],
                    "confidence": 0.8,
                }
            )
        else:
            causes.append(
                {
                    "cause": "页面结构/定位器与脚本预期不一致，或测试数据不满足前置条件",
                    "evidence": observed[:1200],
                    "confidence": 0.5,
                }
            )
        return {
            "observed_error": observed[:4000],
            "inferred_causes": causes,
            "suggestions": [
                "先核对 failure_message 与 traceback 中的实际值，"
                "再检查用例 expected_result 是否准确。",
                "在失败截图中定位实际页面状态，必要时调整 get_by_role/get_by_label 等语义定位器。",
            ],
            "needs_more_info": not bool(message or traceback_text),
        }

    def test_connection(self) -> dict[str, Any]:
        return {
            "ok": True,
            "is_mock": True,
            "provider": self.provider_name,
            "model": self.model,
            "latency_ms": 0,
            "message": "Mock 模式：不会调用真实模型",
        }

    def close(self) -> None:
        return None
