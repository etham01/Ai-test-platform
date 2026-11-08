from __future__ import annotations

import time
from typing import Any

import httpx

from app.ai.prompt_manager import PromptManager
from app.ai.providers.base import LLMError, LLMResult


class OpenAICompatibleProvider:
    provider_name = "openai_compatible"
    is_mock = False

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        max_retries: int = 2,
        temperature: float = 0.2,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_retries = max(0, max_retries)
        self.temperature = temperature
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
        )

    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _extract_content(self, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMError("LLM_EMPTY_RESPONSE", "模型响应缺少 choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise LLMError("LLM_EMPTY_RESPONSE", "模型响应缺少 message")
        content = message.get("content")
        if isinstance(content, list):
            parts = [
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict)
            ]
            content = "".join(parts)
        if not isinstance(content, str) or not content.strip():
            raise LLMError("LLM_EMPTY_RESPONSE", "模型返回了空内容")
        return content

    def generate(
        self,
        task: str,
        payload: dict[str, Any],
        *,
        prompt_version: str = "v1",
        repair_note: str | None = None,
    ) -> LLMResult:
        rendered = PromptManager.render(
            task, payload, version=prompt_version, repair_note=repair_note
        )
        request_body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": rendered.system},
                {"role": "user", "content": rendered.user},
            ],
            "temperature": self.temperature,
            "stream": False,
        }

        last_error: LLMError | None = None
        started = time.perf_counter()
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.post(
                    self._endpoint(),
                    headers=self._headers(),
                    json=request_body,
                )
            except httpx.TimeoutException:
                last_error = LLMError("LLM_TIMEOUT", "模型服务请求超时")
            except httpx.HTTPError as exc:
                last_error = LLMError("LLM_NETWORK_ERROR", f"模型服务网络错误: {exc}")
            else:
                if response.status_code in {401, 403}:
                    raise LLMError("LLM_AUTH_FAILED", "模型服务鉴权失败，请检查 API Key")
                if response.status_code == 429:
                    last_error = LLMError("LLM_RATE_LIMITED", "模型服务限流")
                elif response.status_code >= 500:
                    last_error = LLMError(
                        "LLM_UPSTREAM_ERROR",
                        f"模型服务返回 HTTP {response.status_code}",
                    )
                elif response.status_code >= 400:
                    raise LLMError(
                        "LLM_REQUEST_FAILED",
                        f"模型服务返回 HTTP {response.status_code}",
                        details=response.text[:300],
                    )
                else:
                    try:
                        data = response.json()
                    except ValueError as exc:
                        raise LLMError(
                            "LLM_INVALID_RESPONSE", "模型服务返回了非 JSON 响应"
                        ) from exc
                    content = self._extract_content(data)
                    usage = data.get("usage") if isinstance(data, dict) else None
                    usage = usage if isinstance(usage, dict) else {}
                    return LLMResult(
                        content=content,
                        provider=self.provider_name,
                        model=self.model,
                        is_mock=False,
                        prompt_version=rendered.version,
                        prompt_tokens=usage.get("prompt_tokens"),
                        completion_tokens=usage.get("completion_tokens"),
                        duration_ms=round((time.perf_counter() - started) * 1000),
                        raw=data if isinstance(data, dict) else {},
                    )

            if attempt < self.max_retries:
                time.sleep(min(4.0, 0.5 * (2**attempt)))

        raise last_error or LLMError("LLM_REQUEST_FAILED", "模型服务请求失败")

    def test_connection(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            response = self._client.post(
                self._endpoint(),
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Reply with OK"}],
                    "temperature": 0,
                    "max_tokens": 8,
                    "stream": False,
                },
            )
        except httpx.TimeoutException as exc:
            raise LLMError("LLM_TIMEOUT", "模型服务连接超时") from exc
        except httpx.HTTPError as exc:
            raise LLMError("LLM_NETWORK_ERROR", f"模型服务网络错误: {exc}") from exc

        if response.status_code in {401, 403}:
            raise LLMError("LLM_AUTH_FAILED", "模型服务鉴权失败，请检查 API Key")
        if response.status_code >= 400:
            raise LLMError(
                "LLM_REQUEST_FAILED",
                f"模型服务返回 HTTP {response.status_code}",
                details=response.text[:300],
            )
        return {
            "ok": True,
            "is_mock": False,
            "provider": self.provider_name,
            "model": self.model,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "message": "连接成功",
        }

    def close(self) -> None:
        self._client.close()
