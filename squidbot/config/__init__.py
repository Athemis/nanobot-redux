"""Configuration module for squidbot."""

from squidbot.config.loader import get_config_path, load_config
from squidbot.config.schema import Config

__all__ = ["Config", "load_config", "get_config_path"]
