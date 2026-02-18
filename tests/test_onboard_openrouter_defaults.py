import pytest

from nanobot.cli.commands import (
    OPENROUTER_DEFAULT_EXTRA_HEADERS,
    _make_provider,
    _resolve_runtime_extra_headers,
    _seed_openrouter_attribution_headers,
)
from nanobot.config.schema import Config
from nanobot.providers.openai_provider import OpenAIProvider


def test_do_not_override_intentionally_empty_openrouter_headers() -> None:
    config = Config()
    config.providers.openrouter.extra_headers = {}

    _seed_openrouter_attribution_headers(config)

    assert config.providers.openrouter.extra_headers == {}


@pytest.mark.parametrize(
    ("extra_headers", "expected"),
    [
        (None, OPENROUTER_DEFAULT_EXTRA_HEADERS),
        ({}, {}),
    ],
)
def test_runtime_fallback_handles_unset_and_explicit_empty(
    extra_headers: dict[str, str] | None, expected: dict[str, str]
) -> None:
    resolved = _resolve_runtime_extra_headers("openrouter", extra_headers)

    assert resolved == expected


def test_make_provider_applies_openrouter_runtime_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("nanobot.providers.openai_provider.OpenAIProvider", DummyProvider)

    config = Config()
    config.providers.openrouter.api_key = "sk-test"
    config.providers.openrouter.extra_headers = None
    config.agents.defaults.model = "openrouter/anthropic/claude-opus-4-5"

    _make_provider(config)

    assert captured["provider_name"] == "openrouter"
    assert captured["extra_headers"] == OPENROUTER_DEFAULT_EXTRA_HEADERS


def test_openrouter_prefix_stripped_before_forwarding_to_api() -> None:
    """Legacy model strings like 'openrouter/anthropic/claude-3' must lose the 'openrouter/' prefix."""
    provider = OpenAIProvider(
        api_key="sk-or-test",
        default_model="openrouter/anthropic/claude-opus-4-5",
        provider_name="openrouter",
    )

    resolved = provider._resolve_model("openrouter/anthropic/claude-opus-4-5")

    assert resolved == "anthropic/claude-opus-4-5"


def test_openrouter_bare_model_name_unchanged() -> None:
    """Model strings without the 'openrouter/' prefix are forwarded unchanged."""
    provider = OpenAIProvider(
        api_key="sk-or-test",
        default_model="anthropic/claude-opus-4-5",
        provider_name="openrouter",
    )

    resolved = provider._resolve_model("anthropic/claude-opus-4-5")

    assert resolved == "anthropic/claude-opus-4-5"


def test_make_provider_passes_openai_codex_ssl_verify_from_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("nanobot.providers.openai_codex_provider.OpenAICodexProvider", DummyProvider)

    config = Config()
    config.agents.defaults.model = "openai-codex/gpt-5.2-codex"
    config.providers.openai_codex.ssl_verify = False

    _make_provider(config)

    assert captured["default_model"] == "openai-codex/gpt-5.2-codex"
    assert captured["ssl_verify"] is False
