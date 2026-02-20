"""Tests for SessionManager — scoping and legacy fallback."""

import json
from pathlib import Path

from nanobot.session.manager import Session, SessionManager


def _write_session_to(path: Path, session: Session) -> None:
    """Write a session JSONL file directly to the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        metadata = {
            "_type": "metadata",
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "metadata": session.metadata,
            "last_consolidated": session.last_consolidated,
        }
        f.write(json.dumps(metadata) + "\n")
        for msg in session.messages:
            f.write(json.dumps(msg) + "\n")


def test_sessions_stored_in_workspace(tmp_path):
    """New sessions are written to <workspace>/sessions/, not ~/.nanobot/sessions/."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    manager = SessionManager(workspace)
    session = manager.get_or_create("chan:user1")
    session.add_message("user", "hello")
    manager.save(session)

    assert (workspace / "sessions").exists()
    assert any((workspace / "sessions").glob("*.jsonl"))


def test_legacy_session_fallback(tmp_path, monkeypatch):
    """Sessions missing from workspace/sessions/ are loaded from ~/.nanobot/sessions/."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    manager = SessionManager(workspace)

    # Write a session directly into the legacy location
    legacy_session = Session(key="chan:legacy")
    legacy_session.add_message("user", "legacy message")
    legacy_path = manager._get_legacy_session_path("chan:legacy")
    _write_session_to(legacy_path, legacy_session)

    # workspace/sessions/ has no matching file — should fall back
    loaded = manager.get_or_create("chan:legacy")
    assert len(loaded.messages) == 1
    assert loaded.messages[0]["content"] == "legacy message"


def test_workspace_session_takes_priority_over_legacy(tmp_path, monkeypatch) -> None:
    """workspace/sessions/ takes priority when both workspace and legacy sessions exist."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    manager = SessionManager(workspace)

    # Write a session to legacy
    legacy_session = Session(key="chan:both")
    legacy_session.add_message("user", "from legacy")
    _write_session_to(manager._get_legacy_session_path("chan:both"), legacy_session)

    # Write a different session to workspace
    workspace_session = Session(key="chan:both")
    workspace_session.add_message("user", "from workspace")
    manager.save(workspace_session)

    loaded = manager.get_or_create("chan:both")
    assert loaded.messages[0]["content"] == "from workspace"


def test_legacy_migration_failure_is_graceful(tmp_path, monkeypatch) -> None:
    """If the legacy session file cannot be moved, _load falls back gracefully."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    manager = SessionManager(workspace)

    legacy_session = Session(key="chan:migrate")
    legacy_session.add_message("user", "old message")
    _write_session_to(manager._get_legacy_session_path("chan:migrate"), legacy_session)

    # Simulate shutil.move raising an OSError (e.g., cross-device link)
    def failing_move(*args, **kwargs):
        raise OSError("cross-device link")

    monkeypatch.setattr("nanobot.session.manager.shutil.move", failing_move)

    # Should not raise — returns None gracefully
    result = manager._load("chan:migrate")
    assert result is None


def test_list_sessions_returns_original_key_for_keys_with_underscores(tmp_path) -> None:
    """list_sessions must return the exact original key, not a path-derived reconstruction."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    manager = SessionManager(workspace)

    # Key with underscore — path-stem reconstruction would produce wrong result
    session = manager.get_or_create("my_channel:chat_id")
    session.add_message("user", "hello")
    manager.save(session)

    sessions = manager.list_sessions()
    keys = [s["key"] for s in sessions]
    assert "my_channel:chat_id" in keys
    assert "my:channel:chat:id" not in keys


def test_list_sessions_returns_original_key_for_simple_keys(tmp_path) -> None:
    """list_sessions returns the correct key for a simple channel:id key."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    manager = SessionManager(workspace)

    session = manager.get_or_create("matrix:!roomid")
    session.add_message("user", "hi")
    manager.save(session)

    sessions = manager.list_sessions()
    keys = [s["key"] for s in sessions]
    assert "matrix:!roomid" in keys
