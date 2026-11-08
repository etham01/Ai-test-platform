from __future__ import annotations

import pytest
from app.ai.output_parser import OutputParseError, extract_json_object
from app.ai.providers.base import LLMResult
from app.ai.service import generate_structured
from pydantic import BaseModel


class SmallModel(BaseModel):
    value: int


class RepairingProvider:
    provider_name = "fake"
    model = "fake-v1"
    is_mock = True

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, task, payload, *, prompt_version="v1", repair_note=None):
        self.calls += 1
        content = "not json" if self.calls == 1 else '{"value": 7}'
        return LLMResult(
            content=content,
            provider=self.provider_name,
            model=self.model,
            is_mock=True,
            prompt_version=prompt_version,
        )

    def test_connection(self):
        return {"ok": True}

    def close(self):
        return None


def test_extract_json_from_fence():
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json_object('prefix {"a": 2} suffix') == {"a": 2}


def test_invalid_json_raises():
    with pytest.raises(OutputParseError):
        extract_json_object("no json here")


def test_generate_structured_repairs_once_then_succeeds():
    provider = RepairingProvider()
    validated, result = generate_structured(
        provider,
        "case_generation",
        {},
        SmallModel,
        max_repairs=1,
    )
    assert provider.calls == 2
    assert validated.value == 7
    assert result.content == '{"value": 7}'
