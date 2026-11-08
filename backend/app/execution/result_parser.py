from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def parse_junit_xml(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []

    results: list[dict[str, Any]] = []
    for testcase in root.iter("testcase"):
        name = testcase.get("name") or "unknown"
        classname = testcase.get("classname") or ""
        try:
            duration_ms = int(float(testcase.get("time") or 0) * 1000)
        except ValueError:
            duration_ms = 0
        status = "passed"
        failure_message: str | None = None
        traceback_text: str | None = None
        for child in testcase:
            tag = child.tag.lower()
            if tag in {"failure", "error"}:
                status = "failed" if tag == "failure" else "error"
                failure_message = (child.get("message") or "").strip()[:4000] or None
                traceback_text = (child.text or "").strip()[:8000] or None
                break
            if tag == "skipped":
                status = "skipped"
                failure_message = (child.get("message") or "").strip()[:4000] or None
                break
        results.append(
            {
                "name": name,
                "classname": classname,
                "node_id": f"{classname}::{name}" if classname else name,
                "status": status,
                "duration_ms": duration_ms,
                "failure_message": failure_message,
                "traceback": traceback_text,
            }
        )
    return results
