"""Tests for camelCase/snake_case config handling via Pydantic alias_generator."""

import json
import warnings

import pytest

from nanobot.config.loader import (
    _migrate_config,
    get_config_path,
    get_data_dir,
    load_config,
    save_config,
)
from nanobot.config.schema import Config


def test_model_validate_accepts_camel_case_top_level_tool_keys() -> None:
    data = {
        "tools": {
            "restrictToWorkspace": True,
        }
    }

    config = Config.model_validate(data)

    assert config.tools.restrict_to_workspace is True


def test_model_validate_accepts_snake_case_keys() -> None:
    """populate_by_name=True means snake_case is also accepted."""
    data = {
        "tools": {
            "restrict_to_workspace": True,
        }
    }

    config = Config.model_validate(data)

    assert config.tools.restrict_to_workspace is True


def test_model_validate_maps_openai_codex_ssl_verify() -> None:
    data = {
        "providers": {
            "openaiCodex": {
                "sslVerify": False,
            }
        }
    }

    config = Config.model_validate(data)

    assert config.providers.openai_codex.ssl_verify is False


def test_model_validate_maps_openai_prompt_caching_fields() -> None:
    data = {
        "providers": {
            "openai": {
                "promptCachingEnabled": True,
                "promptCacheRetention": "24h",
            }
        }
    }

    config = Config.model_validate(data)

    assert config.providers.openai.prompt_caching_enabled is True
    assert config.providers.openai.prompt_cache_retention == "24h"


def test_provider_prompt_caching_enabled_defaults_to_none() -> None:
    config = Config()

    assert config.providers.openai.prompt_caching_enabled is None


def test_model_validate_maps_provider_fields_and_preserves_header_entry_keys() -> None:
    data = {
        "providers": {
            "openrouter": {
                "apiBase": "https://openrouter.ai/api/v1",
                "extraHeaders": {
                    "HTTP-Referer": "https://example.com",
                    "X-Title": "nanobot",
                },
            }
        }
    }

    config = Config.model_validate(data)

    assert config.providers.openrouter.api_base == "https://openrouter.ai/api/v1"
    assert config.providers.openrouter.extra_headers == {
        "HTTP-Referer": "https://example.com",
        "X-Title": "nanobot",
    }


def test_model_validate_preserves_mcp_env_var_names() -> None:
    """env dict keys (e.g. OPENAI_API_KEY) must not be snake_case-converted."""
    data = {
        "tools": {
            "mcpServers": {
                "demo": {
                    "command": "npx",
                    "env": {
                        "OPENAI_API_KEY": "test_key",
                        "MyCustomToken": "abc",
                    },
                }
            }
        }
    }

    config = Config.model_validate(data)
    env = config.tools.mcp_servers["demo"].env

    assert env["OPENAI_API_KEY"] == "test_key"
    assert env["MyCustomToken"] == "abc"


def test_model_dump_by_alias_outputs_camel_case() -> None:
    data = {
        "tools": {
            "restrictToWorkspace": True,
            "mcpServers": {
                "demo": {
                    "command": "npx",
                    "env": {"OPENAI_API_KEY": "test_key"},
                }
            },
        }
    }

    config = Config.model_validate(data)
    dumped = config.model_dump(by_alias=True)

    assert dumped["tools"]["restrictToWorkspace"] is True
    assert "mcpServers" in dumped["tools"]
    assert dumped["tools"]["mcpServers"]["demo"]["env"]["OPENAI_API_KEY"] == "test_key"


def test_model_dump_by_alias_preserves_extra_headers_entry_names() -> None:
    """extra_headers dict keys must survive the round-trip unchanged."""
    data = {
        "providers": {
            "openrouter": {
                "extraHeaders": {
                    "X_Custom_Header": "value",
                    "X_Trace_ID": "trace",
                }
            }
        }
    }

    config = Config.model_validate(data)
    dumped = config.model_dump(by_alias=True)
    headers = dumped["providers"]["openrouter"]["extraHeaders"]

    assert headers["X_Custom_Header"] == "value"
    assert headers["X_Trace_ID"] == "trace"


def test_model_dump_by_alias_outputs_openai_prompt_caching_fields() -> None:
    config = Config.model_validate(
        {
            "providers": {
                "openai": {
                    "promptCachingEnabled": True,
                    "promptCacheRetention": "24h",
                }
            }
        }
    )

    dumped = config.model_dump(by_alias=True)

    assert dumped["providers"]["openai"]["promptCachingEnabled"] is True
    assert dumped["providers"]["openai"]["promptCacheRetention"] == "24h"


def test_model_validate_accepts_e2ee_enabled_with_correct_casing() -> None:
    """e2ee_enabled has alias 'e2eeEnabled'; to_camel() would wrongly produce 'e2EeEnabled'."""
    data = {"channels": {"matrix": {"e2eeEnabled": False}}}

    config = Config.model_validate(data)

    assert config.channels.matrix.e2ee_enabled is False


def test_model_dump_outputs_e2ee_enabled_with_correct_casing() -> None:
    data = {"channels": {"matrix": {"e2eeEnabled": False}}}

    config = Config.model_validate(data)
    dumped = config.model_dump(by_alias=True)

    assert "e2eeEnabled" in dumped["channels"]["matrix"]
    assert "e2EeEnabled" not in dumped["channels"]["matrix"]


def test_migrate_config_moves_exec_restrict_to_workspace() -> None:
    """Old configs stored restrictToWorkspace under tools.exec; migration lifts it to tools."""
    data = {"tools": {"exec": {"restrictToWorkspace": True}}}

    migrated = _migrate_config(data)

    assert migrated["tools"]["restrictToWorkspace"] is True
    assert "restrictToWorkspace" not in migrated["tools"]["exec"]


def test_migrate_config_does_not_overwrite_existing_tools_restrict() -> None:
    """If tools.restrictToWorkspace already exists, the exec value must not overwrite it."""
    data = {"tools": {"restrictToWorkspace": False, "exec": {"restrictToWorkspace": True}}}

    migrated = _migrate_config(data)

    assert migrated["tools"]["restrictToWorkspace"] is False


def test_migrate_config_warns_for_removed_anthropic_provider() -> None:
    """Config with providers.anthropic triggers a deprecation warning and key is removed."""
    data = {"providers": {"anthropic": {"apiKey": "sk-ant-123"}}}

    with pytest.warns(DeprecationWarning, match="providers.anthropic is no longer supported"):
        migrated = _migrate_config(data)

    assert "anthropic" not in migrated.get("providers", {})


def test_migrate_config_warns_for_removed_gemini_provider() -> None:
    """Config with providers.gemini triggers a deprecation warning and key is removed."""
    data = {"providers": {"gemini": {"apiKey": "AI-123"}}}

    with pytest.warns(DeprecationWarning, match="providers.gemini is no longer supported"):
        migrated = _migrate_config(data)

    assert "gemini" not in migrated.get("providers", {})


def test_migrate_config_warns_for_removed_custom_provider() -> None:
    """Config with providers.custom triggers a deprecation warning and key is removed."""
    data = {"providers": {"custom": {"apiBase": "http://localhost:8000/v1"}}}

    with pytest.warns(DeprecationWarning, match="providers.custom is no longer supported"):
        migrated = _migrate_config(data)

    assert "custom" not in migrated.get("providers", {})


def test_migrate_config_no_warning_for_supported_providers() -> None:
    """Config with supported providers does not trigger any deprecation warning."""
    data = {"providers": {"openrouter": {"apiKey": "sk-or-123"}}}

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        _migrate_config(data)  # raises if any DeprecationWarning is emitted


def test_round_trip_preserves_camel_case_structure() -> None:
    """Load camelCase JSON → dump by_alias=True → same camelCase shape."""
    data = {
        "providers": {
            "openrouter": {
                "apiBase": "https://openrouter.ai/api/v1",
                "extraHeaders": {
                    "HTTP-Referer": "https://example.com",
                },
            }
        },
        "tools": {
            "restrictToWorkspace": True,
        },
    }

    config = Config.model_validate(data)
    dumped = config.model_dump(by_alias=True)

    assert dumped["providers"]["openrouter"]["apiBase"] == "https://openrouter.ai/api/v1"
    assert (
        dumped["providers"]["openrouter"]["extraHeaders"]["HTTP-Referer"] == "https://example.com"
    )
    assert dumped["tools"]["restrictToWorkspace"] is True


# ── Additional tests for loader functions ─────────────────────────────────────


def test_get_config_path_returns_default() -> None:
    path = get_config_path()
    assert path.name == "config.json"
    assert ".nanobot" in str(path)


def test_get_data_dir_returns_path() -> None:
    d = get_data_dir()
    assert d.exists()


def test_load_config_from_existing_file(tmp_path) -> None:
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text('{"model": "gpt-4o"}', encoding="utf-8")
    cfg = load_config(cfg_file)
    assert isinstance(cfg, Config)


def test_load_config_returns_default_when_file_missing(tmp_path) -> None:
    cfg = load_config(tmp_path / "nonexistent.json")
    assert isinstance(cfg, Config)


def test_load_config_returns_default_on_invalid_json(tmp_path) -> None:
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("not-json", encoding="utf-8")
    cfg = load_config(cfg_file)
    assert isinstance(cfg, Config)


def test_save_config_writes_valid_json(tmp_path) -> None:
    cfg = Config()
    out = tmp_path / "out.json"
    save_config(cfg, out)
    data = json.loads(out.read_text())
    assert isinstance(data, dict)


def test_save_config_creates_parent_dirs(tmp_path) -> None:
    cfg = Config()
    out = tmp_path / "sub" / "dir" / "config.json"
    save_config(cfg, out)
    assert out.exists()
