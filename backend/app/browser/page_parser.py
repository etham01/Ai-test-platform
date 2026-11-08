from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, Response

SNAPSHOT_SCRIPT_PATH = Path(__file__).resolve().parent / "extractors" / "page_snapshot.js"

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
MAX_DOM_CHARS = 200_000
MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024


def sanitize_text(value: str | None) -> str:
    if not value:
        return ""
    return _PHONE_RE.sub("[phone]", _EMAIL_RE.sub("[email]", value))


def _clip(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


@dataclass
class ParsedElement:
    element_type: str
    tag: str
    role: str | None
    accessible_name: str | None
    label: str | None
    placeholder: str | None
    text: str | None
    element_id: str | None
    name: str | None
    input_type: str | None
    href: str | None
    selector_candidates: dict[str, Any] | None
    is_sensitive: bool
    attributes: dict[str, Any] | None


@dataclass
class ParsedLink:
    href: str
    text: str = ""


@dataclass
class ParsedForm:
    action: str
    method: str
    fields: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedPage:
    url: str
    final_url: str
    title: str
    text_summary: str
    dom_html: str
    screenshot_png: bytes
    http_status: int | None
    content_type: str | None
    elements: list[ParsedElement]
    links: list[ParsedLink]
    forms: list[ParsedForm]


@lru_cache(maxsize=1)
def _snapshot_script() -> str:
    return SNAPSHOT_SCRIPT_PATH.read_text(encoding="utf-8")


class PageParser:
    @staticmethod
    def parse(page: Page, response: Response | None = None) -> ParsedPage:
        data = page.evaluate(_snapshot_script())
        if not isinstance(data, dict):
            raise RuntimeError("页面快照脚本返回了非结构化结果")

        elements: list[ParsedElement] = []
        for item in data.get("elements", []) or []:
            if not isinstance(item, dict):
                continue
            candidates = item.get("selector_candidates")
            attributes = item.get("attributes")
            elements.append(
                ParsedElement(
                    element_type=_clip(item.get("element_type"), 32) or "other",
                    tag=_clip(item.get("tag"), 32) or "div",
                    role=_clip(item.get("role"), 64),
                    accessible_name=_clip(item.get("accessible_name"), 512),
                    label=_clip(item.get("label"), 512),
                    placeholder=_clip(item.get("placeholder"), 512),
                    text=_clip(sanitize_text(item.get("text")), 1024),
                    element_id=_clip(item.get("element_id"), 256),
                    name=_clip(item.get("name"), 256),
                    input_type=_clip(item.get("input_type"), 64),
                    href=_clip(item.get("href"), 2048),
                    selector_candidates=candidates if isinstance(candidates, dict) else None,
                    is_sensitive=bool(item.get("is_sensitive")),
                    attributes=attributes if isinstance(attributes, dict) else None,
                )
            )

        links = [
            ParsedLink(
                href=_clip(item.get("href"), 2048) or "",
                text=_clip(sanitize_text(item.get("text")), 300) or "",
            )
            for item in data.get("links", []) or []
            if isinstance(item, dict) and item.get("href")
        ]
        forms = [
            ParsedForm(
                action=_clip(item.get("action"), 2048) or "",
                method=(_clip(item.get("method"), 16) or "get").lower(),
                fields=item.get("fields") or [],
            )
            for item in data.get("forms", []) or []
            if isinstance(item, dict)
        ]

        screenshot = b""
        try:
            screenshot = page.screenshot(full_page=True, type="png")
            if len(screenshot) > MAX_SCREENSHOT_BYTES:
                screenshot = page.screenshot(full_page=False, type="png")
        except Exception:
            screenshot = b""

        headers = response.headers if response is not None else {}
        return ParsedPage(
            url=page.url,
            final_url=page.url,
            title=_clip(sanitize_text(data.get("title")), 512) or "",
            text_summary=_clip(sanitize_text(data.get("bodyText")), 8000) or "",
            dom_html=str(data.get("dom") or "")[:MAX_DOM_CHARS],
            screenshot_png=screenshot,
            http_status=response.status if response is not None else None,
            content_type=headers.get("content-type"),
            elements=elements,
            links=links,
            forms=forms,
        )
