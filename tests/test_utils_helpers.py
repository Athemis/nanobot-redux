"""Tests for utility helpers."""

from pathlib import Path

import pytest

from nanobot.utils.helpers import (
    ensure_dir,
    get_data_path,
    get_sessions_path,
    get_skills_path,
    get_workspace_path,
    parse_session_key,
    safe_filename,
    timestamp,
    truncate_string,
)


def test_ensure_dir_creates_nested(tmp_path):
    target = tmp_path / "a" / "b" / "c"
    result = ensure_dir(target)
    assert result.exists()
    assert result == target


def test_get_data_path_returns_nanobot_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = get_data_path()
    assert result == tmp_path / ".nanobot"
    assert result.exists()


def test_get_workspace_path_default(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = get_workspace_path()
    assert result == tmp_path / ".nanobot" / "workspace"
    assert result.exists()


def test_get_workspace_path_explicit(tmp_path):
    custom = tmp_path / "myws"
    result = get_workspace_path(str(custom))
    assert result == custom
    assert result.exists()


def test_get_sessions_path(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = get_sessions_path()
    assert result == tmp_path / ".nanobot" / "sessions"
    assert result.exists()


def test_get_skills_path_with_workspace(tmp_path):
    result = get_skills_path(workspace=tmp_path)
    assert result == tmp_path / "skills"
    assert result.exists()


def test_get_skills_path_default(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = get_skills_path()
    assert result.name == "skills"


def test_timestamp_returns_iso_string():
    from datetime import datetime

    ts = timestamp()
    assert "T" in ts and "-" in ts  # ISO format contains both
    datetime.fromisoformat(ts)  # raises if not a valid ISO datetime string


def test_truncate_string_no_truncation():
    assert truncate_string("short", 100) == "short"


def test_truncate_string_truncates():
    result = truncate_string("hello world", max_len=8)
    assert len(result) == 8
    assert result.endswith("...")


def test_safe_filename_replaces_unsafe_chars():
    result = safe_filename('foo<bar>:baz"qux')
    assert "<" not in result
    assert ">" not in result
    assert ":" not in result


def test_parse_session_key_valid():
    channel, chat_id = parse_session_key("matrix:!room123")
    assert channel == "matrix"
    assert chat_id == "!room123"


def test_parse_session_key_preserves_colon_in_chat_id():
    channel, chat_id = parse_session_key("email:user@host.com")
    assert channel == "email"
    assert chat_id == "user@host.com"


def test_parse_session_key_invalid_raises():
    with pytest.raises(ValueError, match="Invalid session key"):
        parse_session_key("no-colon-here")
