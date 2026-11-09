"""Tests for the Gemini wrapper (no network calls)."""
import pytest

import core.llm
from core.llm import AINotConfiguredError, AIServiceError, GeminiClient


class FakeGenaiClient:
    created = 0

    def __init__(self, api_key):
        FakeGenaiClient.created += 1
        self.models = self

    def generate_content(self, model, contents):
        if contents == "boom":
            raise RuntimeError("quota exceeded")

        class Response:
            text = f"{model}:{contents}"
        return Response()


@pytest.fixture
def fake_genai(monkeypatch):
    FakeGenaiClient.created = 0
    monkeypatch.setattr(core.llm.genai, "Client", FakeGenaiClient)


def test_client_without_key_raises(fake_genai):
    client = GeminiClient("")
    assert not client.is_configured
    with pytest.raises(AINotConfiguredError):
        client.generate("hi")


def test_client_reuses_sdk_client(fake_genai):
    client = GeminiClient("key")
    assert client.generate("a") == "gemini-flash-lite-latest:a"
    assert client.generate("b", vision=True) == "gemini-3.6-flash:b"
    assert FakeGenaiClient.created == 1


def test_changing_key_recreates_sdk_client(fake_genai):
    client = GeminiClient("key")
    client.generate("a")
    client.set_api_key("other")
    client.generate("b")
    assert FakeGenaiClient.created == 2


def test_sdk_errors_are_wrapped(fake_genai):
    with pytest.raises(AIServiceError, match="quota exceeded"):
        GeminiClient("key").generate("boom")
