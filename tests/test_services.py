"""Tests for the Gemini wrapper (no network calls)."""
import pytest

import core.config
import core.llm
from core.llm import AINotConfiguredError, AIServiceError, GeminiClient
from core.services import build_services


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


@pytest.fixture
def services(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(core.config, "is_frozen", lambda: True)  # Ignore a developer's local api_key.txt
    return build_services(str(tmp_path / "config.json"), str(tmp_path / "log.txt"), str(tmp_path / "log.json"))


def test_services_share_one_exclusion_policy(services, tmp_path):
    services.set_excluded_folders([str(tmp_path / "private")])

    path = str(tmp_path / "private" / "a.txt")
    assert services.cleaner.exclusion.is_excluded(path)
    assert services.organizer.exclusion.is_excluded(path)
    assert services.watcher.exclusion.is_excluded(path)
    assert services.config.get("excluded_folders") == [str(tmp_path / "private")]


def test_services_default_to_zipzap_ai_without_a_key(services):
    assert services.llm.active_name == "zipzap"
    assert services.llm.is_configured
    assert services.zipzap.base_url.startswith("https://")


def test_services_share_one_llm_client(services):
    services.set_ai_provider("gemini")
    assert not services.llm.is_configured
    services.set_api_key("new-key")
    assert services.organizer.llm is services.llm
    assert services.assistant.llm is services.llm
    assert services.llm.is_configured

    services.set_api_key("")
    assert not services.llm.is_configured
