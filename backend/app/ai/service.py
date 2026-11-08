from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.output_parser import OutputParseError, extract_json_object
from app.ai.providers.base import LLMError, LLMProvider, LLMResult

T = TypeVar("T", bound=BaseModel)


def generate_structured(
    provider: LLMProvider,
    task: str,
    payload: dict[str, Any],
    model: type[T],
    *,
    prompt_version: str = "v1",
    max_repairs: int = 2,
) -> tuple[T, LLMResult]:
    """Call the provider and validate JSON, repairing invalid output a bounded number of times."""
    result = provider.generate(task, payload, prompt_version=prompt_version)
    last_error: str | None = None

    for attempt in range(max_repairs + 1):
        try:
            data = extract_json_object(result.content)
            validated = model.model_validate(data)
            return validated, result
        except (OutputParseError, ValidationError) as exc:
            last_error = str(exc)[:1200]
            if attempt >= max_repairs:
                break
            result = provider.generate(
                task,
                payload,
                prompt_version=prompt_version,
                repair_note=(
                    f"第 {attempt + 1} 次输出无法解析或字段不完整：{last_error}。"
                    "请只输出符合约定结构的 JSON。"
                ),
            )

    raise LLMError(
        "LLM_INVALID_OUTPUT",
        "模型输出在有限次修复后仍无法通过 JSON/结构校验",
        details=last_error,
    )
