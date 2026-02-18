"""Tests for Mistral AI provider registration (upstream PR #803 adoption)."""

from nanobot.config.schema import ProviderConfig, ProvidersConfig
from nanobot.providers.registry import PROVIDERS, find_by_model


def test_providers_config_has_mistral_field() -> None:
    config = ProvidersConfig()
    assert hasattr(config, "mistral")
    assert isinstance(config.mistral, ProviderConfig)


def test_mistral_registry_entry_exists() -> None:
    names = [spec.name for spec in PROVIDERS]
    assert "mistral" in names


def test_mistral_spec_api_base() -> None:
    spec = next((s for s in PROVIDERS if s.name == "mistral"), None)
    assert spec is not None, "mistral ProviderSpec not found in PROVIDERS"
    assert spec.default_api_base == "https://api.mistral.ai/v1"


def test_find_by_model_matches_mistral_large() -> None:
    spec = find_by_model("mistral-large-latest")
    assert spec is not None
    assert spec.name == "mistral"


def test_find_by_model_matches_mistral_family_models() -> None:
    for model in ("codestral-latest", "devstral-small-latest", "pixtral-12b", "magistral-medium"):
        spec = find_by_model(model)
        assert spec is not None, f"find_by_model({model!r}) returned None"
        assert spec.name == "mistral", f"expected mistral spec for {model!r}, got {spec.name!r}"


def test_mistral_spec_env_key() -> None:
    spec = next((s for s in PROVIDERS if s.name == "mistral"), None)
    assert spec is not None, "mistral ProviderSpec not found in PROVIDERS"
    assert spec.env_key == "MISTRAL_API_KEY"
