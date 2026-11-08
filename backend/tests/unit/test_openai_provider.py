from __future__ import annotations

import httpx
import pytest
from app.ai.providers.base import LLMError
from app.ai.providers.openai_compatible import OpenAICompatibleProvider


def _provider(handler, *, max_retries: int = 0) -> OpenAICompatibleProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatibleProvider(
        base_url="https://llm.example.com/v1",
        api_key="sk-test",
        model="test-model",
        max_retries=max_retries,
        timeout_seconds=5,
        client=client,
    )


def test_openai_provider_parses_content_and_usage():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer sk-test"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"workflows": []}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            },
        )

    provider = _provider(handler)
    try:
        result = provider.generate("workflow_analysis", {"pages": []})
        assert result.content == '{"workflows": []}'
        assert result.is_mock is False
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 4
        assert result.model == "test-model"
    finally:
        provider.close()


def test_openai_provider_retries_429_then_succeeds():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"workflows": []}'}}]},
        )

    provider = _provider(handler, max_retries=1)
    try:
        result = provider.generate("workflow_analysis", {"pages": []})
        assert result.content == '{"workflows": []}'
        assert calls["count"] == 2
    finally:
        provider.close()


def test_openai_provider_auth_error_is_not_retried():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(401, json={"error": "bad key"})

    provider = _provider(handler, max_retries=3)
    try:
        with pytest.raises(LLMError) as exc:
            provider.generate("workflow_analysis", {"pages": []})
        assert exc.value.code == "LLM_AUTH_FAILED"
        assert calls["count"] == 1
    finally:
        provider.close()


def test_openai_provider_empty_content_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    provider = _provider(handler)
    try:
        with pytest.raises(LLMError) as exc:
            provider.generate("workflow_analysis", {"pages": []})
        assert exc.value.code == "LLM_EMPTY_RESPONSE"
    finally:
        provider.close()
