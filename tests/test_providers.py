import json

import httpx

from paper_agent.models import ModelProfile
from paper_agent.providers import (
    AnthropicClient,
    ModelRole,
    OpenAICompatibleClient,
    create_router,
    extract_json,
)


class FakeResponse:
    def __init__(self, data: dict[str, object]):
        self.data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.data


def test_extract_json_from_fenced_response() -> None:
    assert extract_json('```json\n{"ok": true}\n```') == {"ok": True}


def test_openai_compatible_request(monkeypatch) -> None:
    monkeypatch.setenv("TEST_API_KEY", "secret")
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse({"choices": [{"message": {"content": "result"}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    client = OpenAICompatibleClient(
        ModelProfile(
            provider="openai-compatible",
            model="model-a",
            base_url="https://provider.example/v1",
            api_key_env="TEST_API_KEY",
        )
    )
    assert client.generate(system="system", prompt="prompt") == "result"
    assert captured["url"] == "https://provider.example/v1/chat/completions"
    assert "secret" not in json.dumps(captured.get("json"))


def test_anthropic_request(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_TEST_KEY", "secret")

    def fake_post(url: str, **kwargs: object) -> FakeResponse:
        assert url == "https://api.anthropic.com/v1/messages"
        assert kwargs["headers"]["x-api-key"] == "secret"  # type: ignore[index]
        return FakeResponse({"content": [{"type": "text", "text": "anthropic result"}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    client = AnthropicClient(
        ModelProfile(
            provider="anthropic",
            model="model-b",
            api_key_env="ANTHROPIC_TEST_KEY",
        )
    )
    assert client.generate(system="system", prompt="prompt") == "anthropic result"


def test_openai_compatible_retries_transient_failure(monkeypatch) -> None:
    monkeypatch.setenv("TEST_API_KEY", "secret")
    calls = 0

    def fake_post(url: str, **kwargs: object) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            request = httpx.Request("POST", url)
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)
        return FakeResponse({"choices": [{"message": {"content": "result"}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    client = OpenAICompatibleClient(
        ModelProfile(
            provider="openai-compatible",
            model="model-a",
            api_key_env="TEST_API_KEY",
            max_retries=1,
        )
    )
    assert client.generate(system="system", prompt="prompt") == "result"
    assert calls == 2


def test_model_router_can_use_different_models_by_workflow_role() -> None:
    router = create_router(
        ModelProfile(provider="deterministic", model="default"),
        {
            ModelRole.PLANNING: ModelProfile(provider="deterministic", model="planner"),
            ModelRole.WRITING: ModelProfile(provider="deterministic", model="writer"),
            ModelRole.EVALUATION: ModelProfile(provider="deterministic", model="reviewer"),
        },
    )

    assert router.for_role(ModelRole.ANALYSIS).label == "deterministic:default"
    assert router.for_role(ModelRole.PLANNING).label == "deterministic:planner"
    assert router.for_role(ModelRole.WRITING).label == "deterministic:writer"
    assert router.for_role(ModelRole.EVALUATION).label == "deterministic:reviewer"
