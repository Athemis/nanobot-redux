"""Configuration loading utilities."""

import json
from pathlib import Path
from typing import Any

from nanobot.config.schema import Config


def get_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".nanobot" / "config.json"


def get_data_dir() -> Path:
    """Get the nanobot data directory."""
    from nanobot.utils.helpers import get_data_path
    return get_data_path()


def load_config(config_path: Path | None = None) -> Config:
    """
    Load configuration from file or create default.

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        Loaded configuration object.
    """
    path = config_path or get_config_path()

    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            data = _migrate_config(data)
            return Config.model_validate(convert_keys(data))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load config from {path}: {e}")
            print("Using default configuration.")

    return Config()


def save_config(config: Config, config_path: Path | None = None) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save.
        config_path: Optional path to save to. Uses default if not provided.
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to camelCase format
    data = config.model_dump()
    data = convert_to_camel(data)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _migrate_config(data: dict) -> dict:
    """Migrate old config formats to current."""
    # Move tools.exec.restrictToWorkspace → tools.restrictToWorkspace
    tools = data.get("tools", {})
    exec_cfg = tools.get("exec", {})
    if "restrictToWorkspace" in exec_cfg and "restrictToWorkspace" not in tools:
        tools["restrictToWorkspace"] = exec_cfg.pop("restrictToWorkspace")
    return data


_PRESERVE_ENTRY_KEY_FIELDS = {"extraHeaders", "extra_headers"}


def _is_mcp_env_map_path(path: tuple[str, ...]) -> bool:
    """Whether path points at tools.mcp_servers.<name>.env."""
    return len(path) == 4 and path[0] == "tools" and path[1] == "mcp_servers" and path[3] == "env"


def _is_extra_headers_path(path: tuple[str, ...]) -> bool:
    """Whether path points at an extra_headers map where entry keys are free-form."""
    return bool(path) and path[-1] == "extra_headers"


def convert_keys(data: Any, preserve_entry_keys: bool = False) -> Any:
    """Convert camelCase keys to snake_case for Pydantic."""
    return _convert_keys(data, preserve_entry_keys=preserve_entry_keys)


def _convert_keys(data: Any, preserve_entry_keys: bool, path: tuple[str, ...] = ()) -> Any:
    """Convert keys recursively while preserving selected free-form entry keys."""
    if isinstance(data, dict):
        # Preserve free-form dict keys under selected maps (e.g. headers/env var names).
        if preserve_entry_keys or _is_mcp_env_map_path(path):
            return {
                k: _convert_keys(v, preserve_entry_keys=False, path=path + (k,))
                for k, v in data.items()
            }

        converted: dict[str, Any] = {}
        for key, value in data.items():
            converted_key = camel_to_snake(key)
            preserve_header_entry_keys = key in _PRESERVE_ENTRY_KEY_FIELDS
            converted[converted_key] = _convert_keys(
                value,
                preserve_entry_keys=preserve_header_entry_keys,
                path=path + (converted_key,),
            )
        return converted
    if isinstance(data, list):
        return [_convert_keys(item, preserve_entry_keys=False, path=path) for item in data]
    return data


def convert_to_camel(data: Any) -> Any:
    """Convert snake_case keys to camelCase."""
    return _convert_to_camel(data)


def _convert_to_camel(data: Any, path: tuple[str, ...] = ()) -> Any:
    """Convert keys recursively while preserving selected free-form entry keys."""
    if isinstance(data, dict):
        # Preserve free-form map entry keys (header names/env var names) on save.
        if _is_mcp_env_map_path(path) or _is_extra_headers_path(path):
            return {k: _convert_to_camel(v, path + (k,)) for k, v in data.items()}

        converted: dict[str, Any] = {}
        for key, value in data.items():
            converted_key = snake_to_camel(key)
            converted[converted_key] = _convert_to_camel(value, path + (key,))
        return converted
    if isinstance(data, list):
        return [_convert_to_camel(item, path) for item in data]
    return data


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])
