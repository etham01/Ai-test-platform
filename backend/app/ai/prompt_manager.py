from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Template

from app.ai.prompts.system_prompts import SYSTEM_PROMPTS

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
MAX_PAYLOAD_CHARS = 120_000


class PromptNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class RenderedPrompt:
    task: str
    version: str
    system: str
    user: str


class PromptManager:
    @staticmethod
    def render(
        task: str,
        payload: dict,
        *,
        version: str = "v1",
        repair_note: str | None = None,
    ) -> RenderedPrompt:
        system = SYSTEM_PROMPTS.get(task)
        if not system:
            raise PromptNotFoundError(f"unknown prompt task: {task}")
        path = PROMPT_DIR / f"{task}.{version}.md"
        if not path.is_file():
            raise PromptNotFoundError(f"prompt template missing: {path}")
        payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
        if len(payload_json) > MAX_PAYLOAD_CHARS:
            payload_json = payload_json[:MAX_PAYLOAD_CHARS] + "\n...[payload truncated]"
        user = Template(path.read_text(encoding="utf-8")).render(
            payload_json=payload_json
        )
        if repair_note:
            user += (
                "\n\n## 修复要求\n"
                "上一次输出无法通过 JSON/结构校验。错误摘要如下，请只输出修正后的 JSON：\n"
                f"{repair_note[:1500]}"
            )
        return RenderedPrompt(task=task, version=version, system=system, user=user)
