"""Tests for the on_progress callback in the agent loop."""

from unittest.mock import AsyncMock, MagicMock

from nanobot.agent.loop import AgentLoop


def _make_loop(tmp_path):
    """Create a minimal AgentLoop for testing."""
    from nanobot.bus.queue import MessageBus

    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"

    return AgentLoop(
        bus=bus,
        provider=provider,
        workspace=tmp_path,
        model="test-model",
    )


def test_strip_think_removes_think_blocks():
    """_strip_think removes <think>...</think> blocks."""
    result = AgentLoop._strip_think("<think>internal reasoning</think>actual response")
    assert result == "actual response"


def test_strip_think_multiline():
    """_strip_think handles multiline think blocks."""
    text = "<think>\nline1\nline2\n</think>response"
    result = AgentLoop._strip_think(text)
    assert result == "response"


def test_strip_think_no_block():
    """_strip_think is a no-op when no <think> block present."""
    result = AgentLoop._strip_think("plain text")
    assert result == "plain text"


def test_tool_hint_formats_names(tmp_path):
    """_tool_hint formats tool call names as arrow-prefixed list."""
    loop = _make_loop(tmp_path)
    tc1 = MagicMock()
    tc1.name = "read_file"
    tc2 = MagicMock()
    tc2.name = "write_file"
    result = loop._tool_hint([tc1, tc2])
    assert result == "→ read_file, write_file"


def test_tool_hint_empty_list(tmp_path):
    """_tool_hint returns empty string for no tool calls."""
    loop = _make_loop(tmp_path)
    assert loop._tool_hint([]) == ""


async def test_run_agent_loop_calls_on_progress(tmp_path):
    """on_progress is called with content before tool execution."""
    from nanobot.providers.base import LLMResponse

    loop = _make_loop(tmp_path)

    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.name = "read_file"
    tool_call.arguments = {"path": "/tmp/test"}

    first_response = LLMResponse(
        content="I will read the file now.",
        tool_calls=[tool_call],
    )
    final_response = LLMResponse(content="Done!", tool_calls=[])

    loop.provider.chat = AsyncMock(side_effect=[first_response, final_response])
    loop.tools.execute = AsyncMock(return_value="file contents")
    loop.tools.get_definitions = MagicMock(return_value=[])

    progress_calls: list[str] = []

    async def capture_progress(text: str) -> None:
        progress_calls.append(text)

    messages = [{"role": "user", "content": "read the file"}]
    await loop._run_agent_loop(messages, on_progress=capture_progress)

    assert len(progress_calls) == 1
    assert progress_calls[0] == "I will read the file now."


async def test_run_agent_loop_uses_tool_hint_when_no_content(tmp_path):
    """on_progress falls back to tool hint when LLM content is empty."""
    from nanobot.providers.base import LLMResponse

    loop = _make_loop(tmp_path)

    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.name = "web_search"
    tool_call.arguments = {"query": "test"}

    first_response = LLMResponse(content="", tool_calls=[tool_call])
    final_response = LLMResponse(content="Result!", tool_calls=[])

    loop.provider.chat = AsyncMock(side_effect=[first_response, final_response])
    loop.tools.execute = AsyncMock(return_value="search results")
    loop.tools.get_definitions = MagicMock(return_value=[])

    progress_calls: list[str] = []

    async def capture_progress(text: str) -> None:
        progress_calls.append(text)

    messages = [{"role": "user", "content": "search for something"}]
    await loop._run_agent_loop(messages, on_progress=capture_progress)

    assert len(progress_calls) == 1
    assert "web_search" in progress_calls[0]


async def test_run_agent_loop_no_progress_without_callback(tmp_path):
    """Agent loop works correctly when on_progress is None (default)."""
    from nanobot.providers.base import LLMResponse

    loop = _make_loop(tmp_path)

    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.name = "read_file"
    tool_call.arguments = {"path": "/tmp/test"}

    first_response = LLMResponse(content="reading...", tool_calls=[tool_call])
    final_response = LLMResponse(content="Done!", tool_calls=[])

    loop.provider.chat = AsyncMock(side_effect=[first_response, final_response])
    loop.tools.execute = AsyncMock(return_value="file content")
    loop.tools.get_definitions = MagicMock(return_value=[])

    messages = [{"role": "user", "content": "read a file"}]
    content, tools = await loop._run_agent_loop(messages)
    assert content == "Done!"


async def test_run_agent_loop_strips_think_before_progress(tmp_path):
    """on_progress receives content with <think> blocks stripped."""
    from nanobot.providers.base import LLMResponse

    loop = _make_loop(tmp_path)

    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.name = "read_file"
    tool_call.arguments = {"path": "/tmp/test"}

    first_response = LLMResponse(
        content="<think>internal reasoning</think>Reading the requested file.",
        tool_calls=[tool_call],
    )
    final_response = LLMResponse(content="Done!", tool_calls=[])

    loop.provider.chat = AsyncMock(side_effect=[first_response, final_response])
    loop.tools.execute = AsyncMock(return_value="content")
    loop.tools.get_definitions = MagicMock(return_value=[])

    progress_calls: list[str] = []

    async def capture_progress(text: str) -> None:
        progress_calls.append(text)

    await loop._run_agent_loop(
        [{"role": "user", "content": "read"}], on_progress=capture_progress
    )

    assert progress_calls[0] == "Reading the requested file."
