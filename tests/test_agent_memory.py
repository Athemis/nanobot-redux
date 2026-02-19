"""Tests for MemoryStore."""

from pathlib import Path

from nanobot.agent.memory import MemoryStore


def test_read_long_term_returns_content_when_file_exists(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.memory_file.write_text("remember this", encoding="utf-8")
    assert store.read_long_term() == "remember this"


def test_write_long_term_creates_file(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.write_long_term("new memory")
    assert store.memory_file.read_text(encoding="utf-8") == "new memory"


def test_append_history_appends_with_separator(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.append_history("entry one")
    store.append_history("entry two")
    content = store.history_file.read_text(encoding="utf-8")
    assert "entry one\n\n" in content
    assert "entry two\n\n" in content


def test_get_memory_context_returns_formatted_string(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.write_long_term("important fact")
    ctx = store.get_memory_context()
    assert ctx.startswith("## Long-term Memory")
    assert "important fact" in ctx


def test_get_memory_context_returns_empty_when_no_memory(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    assert store.get_memory_context() == ""
