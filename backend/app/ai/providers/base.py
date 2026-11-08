from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class LLMError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str
    is_mock: bool
    prompt_version: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    duration_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    provider_name: str
    model: str
    is_mock: bool

    def generate(
        self,
        task: str,
        payload: dict[str, Any],
        *,
        prompt_version: str = "v1",
        repair_note: str | None = None,
    ) -> LLMResult: ...

    def test_connection(self) -> dict[str, Any]: ...

    def close(self) -> None: ...
