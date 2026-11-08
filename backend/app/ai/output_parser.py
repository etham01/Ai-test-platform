from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class OutputParseError(ValueError):
    pass


def strip_code_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value


def extract_json_object(text: str) -> dict[str, Any]:
    value = strip_code_fence(text)
    start = value.find("{")
    end = value.rfind("}")
    if start < 0 or end <= start:
        raise OutputParseError("响应中没有找到 JSON 对象")
    candidate = value[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise OutputParseError(f"JSON 解析失败: {exc.msg} (line {exc.lineno})") from exc
    if not isinstance(parsed, dict):
        raise OutputParseError("模型输出必须是 JSON 对象")
    return parsed


def parse_structured(text: str, model: type[T]) -> T:
    data = extract_json_object(text)
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise OutputParseError(f"结构校验失败: {str(exc)[:1200]}") from exc


def summarize_output(text: str, limit: int = 4000) -> str:
    return text.strip()[:limit]
