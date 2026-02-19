"""Tests for skill:name message expansion in _process_message."""

from pathlib import Path
from unittest.mock import MagicMock

from nanobot.agent.loop import AgentLoop
from nanobot.bus.events import InboundMessage
from nanobot.providers.base import LLMResponse


def _make_loop(workspace: Path) -> AgentLoop:
    """Create a minimal AgentLoop with a stubbed provider."""
    from nanobot.bus.queue import MessageBus

    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    return AgentLoop(bus=MessageBus(), provider=provider, workspace=workspace, model="test-model")


def _write_skill(workspace: Path, name: str, body: str) -> None:
    """Write a minimal SKILL.md for testing."""
    skill_dir = workspace / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def _stub_provider(loop: AgentLoop, response_text: str = "Done.") -> list[list]:
    """Stub provider.chat to capture messages and return a simple response."""
    calls: list[list] = []

    async def fake_chat(messages, **kwargs):
        calls.append(list(messages))
        resp = LLMResponse(content=response_text, tool_calls=[])
        return resp

    loop.provider.chat = fake_chat
    loop.tools.get_definitions = MagicMock(return_value=[])
    return calls


async def test_skill_prefix_injects_skill_content(tmp_path: Path) -> None:
    """skill:name expands to include SKILL.md body before the LLM call."""
    _write_skill(tmp_path, "weather", "Run: curl wttr.in/Berlin\n")
    loop = _make_loop(tmp_path)
    calls = _stub_provider(loop)

    msg = InboundMessage(channel="cli", sender_id="user", chat_id="direct", content="skill:weather")
    await loop._process_message(msg)

    # The last user message in the LLM call must contain the skill body
    user_msgs = [m for m in calls[0] if m.get("role") == "user"]
    assert user_msgs, "No user message found in LLM call"
    content = user_msgs[-1]["content"]
    assert isinstance(content, str)
    assert "Run: curl wttr.in/Berlin" in content
    assert "Execute" in content


async def test_skill_prefix_with_args_includes_args(tmp_path: Path) -> None:
    """skill:name args passes args into the expanded message."""
    _write_skill(tmp_path, "weather", "Run: curl wttr.in/{city}\n")
    loop = _make_loop(tmp_path)
    calls = _stub_provider(loop)

    msg = InboundMessage(
        channel="cli", sender_id="user", chat_id="direct", content="skill:weather Duesseldorf"
    )
    await loop._process_message(msg)

    user_msgs = [m for m in calls[0] if m.get("role") == "user"]
    content = user_msgs[-1]["content"]
    assert "Duesseldorf" in content
    assert "Run: curl wttr.in/{city}" in content


async def test_skill_prefix_unknown_skill_passes_through(tmp_path: Path) -> None:
    """skill:nonexistent passes the original message through without crashing."""
    loop = _make_loop(tmp_path)
    calls = _stub_provider(loop)

    msg = InboundMessage(
        channel="cli", sender_id="user", chat_id="direct", content="skill:nonexistent"
    )
    await loop._process_message(msg)

    user_msgs = [m for m in calls[0] if m.get("role") == "user"]
    content = user_msgs[-1]["content"]
    # Original message is passed through unchanged
    assert content == "skill:nonexistent"


async def test_normal_message_not_expanded(tmp_path: Path) -> None:
    """Regular messages without skill: prefix are not modified."""
    _write_skill(tmp_path, "weather", "Run: curl wttr.in/Berlin\n")
    loop = _make_loop(tmp_path)
    calls = _stub_provider(loop)

    msg = InboundMessage(
        channel="cli", sender_id="user", chat_id="direct", content="What is the weather?"
    )
    await loop._process_message(msg)

    user_msgs = [m for m in calls[0] if m.get("role") == "user"]
    content = user_msgs[-1]["content"]
    assert content == "What is the weather?"


async def test_skill_session_history_preserves_original_message(tmp_path: Path) -> None:
    """The original skill:name message (not the expanded one) is stored in session history."""
    _write_skill(tmp_path, "weather", "Run: curl wttr.in/Berlin\n")
    loop = _make_loop(tmp_path)
    _stub_provider(loop)

    msg = InboundMessage(channel="cli", sender_id="user", chat_id="direct", content="skill:weather")
    await loop._process_message(msg)

    session = loop.sessions.get_or_create("cli:direct")
    user_entries = [m for m in session.messages if m.get("role") == "user"]
    assert user_entries, "No user message in session history"
    assert user_entries[-1]["content"] == "skill:weather"
