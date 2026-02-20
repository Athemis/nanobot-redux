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

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.OpenAICodexProvider", DummyProvider
    )

    config = Config()
    config.agents.defaults.model = "openai-codex/gpt-5.2-codex"
    config.providers.openai_codex.ssl_verify = False

    _make_provider(config)

    assert captured["default_model"] == "openai-codex/gpt-5.2-codex"
    assert captured["ssl_verify"] is False


def test_make_provider_passes_openai_prompt_caching_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("nanobot.providers.openai_provider.OpenAIProvider", DummyProvider)

    config = Config()
    config.agents.defaults.model = "openai/gpt-4o"
    config.providers.openai.api_key = "sk-test"
    config.providers.openai.prompt_caching_enabled = True
    config.providers.openai.prompt_cache_retention = "24h"

    _make_provider(config)

    assert captured["prompt_caching_enabled"] is True
    assert captured["prompt_cache_retention"] == "24h"


def test_make_provider_defaults_openai_prompt_caching_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("nanobot.providers.openai_provider.OpenAIProvider", DummyProvider)

    config = Config()
    config.agents.defaults.model = "openai/gpt-4o"
    config.providers.openai.api_key = "sk-test"

    _make_provider(config)

    assert captured["prompt_caching_enabled"] is True


def test_make_provider_defaults_openrouter_prompt_caching_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("nanobot.providers.openai_provider.OpenAIProvider", DummyProvider)

    config = Config()
    config.agents.defaults.model = "openrouter/anthropic/claude-opus-4-5"
    config.providers.openrouter.api_key = "sk-or-test"

    _make_provider(config)

    assert captured["prompt_caching_enabled"] is True


def test_make_provider_explicit_openai_prompt_caching_false_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("nanobot.providers.openai_provider.OpenAIProvider", DummyProvider)

    config = Config()
    config.agents.defaults.model = "openai/gpt-4o"
    config.providers.openai.api_key = "sk-test"
    config.providers.openai.prompt_caching_enabled = False

    _make_provider(config)

    assert captured["prompt_caching_enabled"] is False


# ── Additional OpenAIProvider coverage ────────────────────────────────────────

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402


@pytest.fixture
def basic_provider() -> OpenAIProvider:
    with patch("nanobot.providers.openai_provider.AsyncOpenAI"):
        return OpenAIProvider(api_key="test", default_model="gpt-4o")


def test_get_default_model(basic_provider: OpenAIProvider) -> None:
    assert basic_provider.get_default_model() == "gpt-4o"


def test_resolve_model_strips_gateway_strip_prefix(monkeypatch) -> None:
    import nanobot.providers.openai_provider as oai_mod

    spec = MagicMock()
    spec.strip_model_prefix = True
    spec.model_prefix = None
    spec.default_api_base = None
    spec.model_overrides = []
    monkeypatch.setattr(oai_mod, "find_gateway", lambda *a, **k: spec)
    monkeypatch.setattr(oai_mod, "find_by_model", lambda *a: None)
    monkeypatch.setattr(oai_mod, "find_by_name", lambda *a: None)
    with patch("nanobot.providers.openai_provider.AsyncOpenAI"):
        p = OpenAIProvider(api_key="k", api_base="http://x", provider_name="x")
    assert p._resolve_model("openrouter/gpt-4o") == "gpt-4o"


def test_resolve_model_strips_spec_prefix(monkeypatch) -> None:
    import nanobot.providers.openai_provider as oai_mod

    spec = MagicMock()
    spec.strip_model_prefix = False
    spec.model_prefix = "openrouter"
    spec.default_api_base = None
    spec.model_overrides = []
    monkeypatch.setattr(oai_mod, "find_gateway", lambda *a, **k: None)
    monkeypatch.setattr(oai_mod, "find_by_model", lambda m: spec if "openrouter" in m else None)
    monkeypatch.setattr(oai_mod, "find_by_name", lambda *a: None)
    with patch("nanobot.providers.openai_provider.AsyncOpenAI"):
        p = OpenAIProvider(api_key="k", default_model="openrouter/gpt-4o")
    assert p._resolve_model("openrouter/gpt-4o") == "gpt-4o"


@pytest.mark.asyncio
async def test_chat_includes_tools_kwarg(basic_provider: OpenAIProvider) -> None:
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "ok"
    fake_response.choices[0].message.tool_calls = []
    fake_response.choices[0].finish_reason = "stop"
    fake_response.usage = None
    basic_provider._client.chat.completions.create = AsyncMock(return_value=fake_response)

    tools = [{"type": "function", "function": {"name": "t"}}]
    await basic_provider.chat([{"role": "user", "content": "hi"}], tools=tools)

    call_kwargs = basic_provider._client.chat.completions.create.call_args[1]
    assert "tools" in call_kwargs
    assert call_kwargs["tool_choice"] == "auto"


@pytest.mark.asyncio
async def test_chat_returns_error_response_on_exception(basic_provider: OpenAIProvider) -> None:
    basic_provider._client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("network error")
    )
    response = await basic_provider.chat([{"role": "user", "content": "hi"}])
    assert response.finish_reason == "error"
    assert "network error" in response.content


def test_parse_raises_on_empty_choices(basic_provider: OpenAIProvider) -> None:
    fake_response = MagicMock()
    fake_response.choices = []
    with pytest.raises(ValueError, match="no choices"):
        basic_provider._parse(fake_response)


def test_openrouter_spec_has_prompt_caching_enabled() -> None:
    """OpenRouter ProviderSpec must default prompt caching to enabled."""
    from nanobot.providers.registry import PROVIDERS

    spec = next((s for s in PROVIDERS if s.name == "openrouter"), None)
    assert spec is not None, "OpenRouter ProviderSpec not found"
    assert spec.default_prompt_caching_enabled is True, (
        "OpenRouter supports cache_control; default_prompt_caching_enabled should be True"
    )
