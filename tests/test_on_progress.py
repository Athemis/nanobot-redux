"""Tests for the on_progress callback in the agent loop."""

from typing import Any
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
    """_tool_hint includes a concise preview of the first string argument."""
    loop = _make_loop(tmp_path)
    tc1 = MagicMock()
    tc1.name = "read_file"
    tc2 = MagicMock()
    tc2.name = "write_file"
    tc2.arguments = {"path": "/tmp/out.txt"}
    tc1.arguments = {"path": "/tmp/in.txt"}
    result = loop._tool_hint([tc1, tc2])
    assert result == 'read_file("/tmp/in.txt"), write_file("/tmp/out.txt")'


def test_tool_hint_empty_list(tmp_path):
    """_tool_hint returns empty string for no tool calls."""
    loop = _make_loop(tmp_path)
    assert loop._tool_hint([]) == ""


def test_tool_hint_handles_non_dict_arguments(tmp_path) -> None:
    """_tool_hint falls back to tool name when arguments are malformed."""
    loop = _make_loop(tmp_path)
    tc = MagicMock()
    tc.name = "exec"
    tc.arguments = ["not-a-dict"]
    assert loop._tool_hint([tc]) == "exec"


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

    # PR #833: on_progress fires twice — once with clean text, once with tool hint
    assert len(progress_calls) == 2
    assert progress_calls[0] == "I will read the file now."
    assert progress_calls[1] == 'read_file("/tmp/test")'


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

    # PR #833: no clean text → only the tool hint fires (1 call)
    assert len(progress_calls) == 1
    assert progress_calls[0] == 'web_search("test")'


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


async def test_process_message_publishes_progress_to_bus_by_default(tmp_path) -> None:
    """Without an explicit on_progress, _process_message publishes tool hints via the bus."""
    from nanobot.bus.events import InboundMessage, OutboundMessage
    from nanobot.bus.queue import MessageBus
    from nanobot.providers.base import LLMResponse

    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    loop = AgentLoop(bus=bus, provider=provider, workspace=tmp_path, model="test-model")

    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.name = "read_file"
    tool_call.arguments = {"path": "/tmp/test"}

    loop.provider.chat = AsyncMock(
        side_effect=[
            LLMResponse(content="Let me read that.", tool_calls=[tool_call]),
            LLMResponse(content="Done!", tool_calls=[]),
        ]
    )
    loop.tools.execute = AsyncMock(return_value="file contents")
    loop.tools.get_definitions = MagicMock(return_value=[])

    msg = InboundMessage(
        channel="matrix",
        sender_id="u1",
        chat_id="r1",
        content="read the file",
        metadata={"thread_root_event_id": "$root123"},
    )
    await loop._process_message(msg)

    # The bus outbound queue must contain at least one progress message
    # (tool hint) before the final response.
    outbound: list[OutboundMessage] = []
    while not bus.outbound.empty():
        outbound.append(bus.outbound.get_nowait())

    # _process_message returns the final response but does NOT publish it to the bus —
    # that's ChannelManager's job. The bus should contain only progress messages.
    assert len(outbound) >= 1, "Expected at least one progress message in bus, got none"
    # All progress messages must carry through channel/chat_id and metadata
    for m in outbound:
        assert m.channel == "matrix"
        assert m.chat_id == "r1"
        assert m.metadata.get("thread_root_event_id") == "$root123", (
            "metadata must be forwarded so Matrix can reply in the correct thread"
        )


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

    await loop._run_agent_loop([{"role": "user", "content": "read"}], on_progress=capture_progress)

    assert progress_calls[0] == "Reading the requested file."


async def test_process_message_suppresses_reply_when_message_tool_sent(tmp_path) -> None:
    """_process_message returns None when the message tool already replied in this turn."""
    from nanobot.agent.tools.message import MessageTool
    from nanobot.bus.events import InboundMessage
    from nanobot.bus.queue import MessageBus
    from nanobot.providers.base import LLMResponse

    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    loop = AgentLoop(bus=bus, provider=provider, workspace=tmp_path, model="test-model")

    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.name = "message"
    tool_call.arguments = {"content": "I already replied!"}

    async def _fake_execute(name: str, arguments: Any) -> str:
        mt = loop.tools.get("message")
        if isinstance(mt, MessageTool):
            return await mt.execute(content="I already replied!")
        return ""

    loop.provider.chat = AsyncMock(
        side_effect=[
            LLMResponse(content="", tool_calls=[tool_call]),
            LLMResponse(content="done", tool_calls=[]),
        ]
    )
    loop.tools.execute = AsyncMock(side_effect=_fake_execute)
    loop.tools.get_definitions = MagicMock(return_value=[])

    msg = InboundMessage(channel="ch", sender_id="u1", chat_id="id", content="hi")
    result = await loop._process_message(msg)
    assert result is None, "Should return None when message tool already sent a reply"


async def test_process_message_keeps_reply_when_message_tool_targets_other_chat(tmp_path) -> None:
    """Cross-chat message tool sends must not suppress the current chat's final response."""
    from nanobot.agent.tools.message import MessageTool
    from nanobot.bus.events import InboundMessage
    from nanobot.bus.queue import MessageBus
    from nanobot.providers.base import LLMResponse

    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    loop = AgentLoop(bus=bus, provider=provider, workspace=tmp_path, model="test-model")

    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.name = "message"
    tool_call.arguments = {
        "content": "Sent elsewhere",
        "channel": "matrix",
        "chat_id": "!other:example.org",
    }

    async def _fake_execute(name: str, arguments: Any) -> str:
        mt = loop.tools.get("message")
        if isinstance(mt, MessageTool):
            return await mt.execute(**arguments)
        return ""

    loop.provider.chat = AsyncMock(
        side_effect=[
            LLMResponse(content="", tool_calls=[tool_call]),
            LLMResponse(content="done", tool_calls=[]),
        ]
    )
    loop.tools.execute = AsyncMock(side_effect=_fake_execute)
    loop.tools.get_definitions = MagicMock(return_value=[])

    msg = InboundMessage(channel="ch", sender_id="u1", chat_id="id", content="hi")
    result = await loop._process_message(msg)

    assert result is not None
    assert result.content == "done"


async def test_bus_progress_stops_after_message_tool_replies_in_turn(tmp_path) -> None:
    """Progress hints after an in-turn message send should be suppressed for the same chat."""
    from nanobot.agent.tools.message import MessageTool
    from nanobot.bus.events import InboundMessage, OutboundMessage
    from nanobot.bus.queue import MessageBus
    from nanobot.providers.base import LLMResponse

    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    loop = AgentLoop(bus=bus, provider=provider, workspace=tmp_path, model="test-model")

    message_call = MagicMock()
    message_call.id = "tc1"
    message_call.name = "message"
    message_call.arguments = {"content": "Direct reply"}

    read_call = MagicMock()
    read_call.id = "tc2"
    read_call.name = "read_file"
    read_call.arguments = {"path": "/tmp/x"}

    async def _fake_execute(name: str, arguments: Any) -> str:
        mt = loop.tools.get("message")
        if name == "message" and isinstance(mt, MessageTool):
            return await mt.execute(**arguments)
        return "ok"

    loop.provider.chat = AsyncMock(
        side_effect=[
            LLMResponse(content="", tool_calls=[message_call]),
            LLMResponse(content="", tool_calls=[read_call]),
            LLMResponse(content="final", tool_calls=[]),
        ]
    )
    loop.tools.execute = AsyncMock(side_effect=_fake_execute)
    loop.tools.get_definitions = MagicMock(return_value=[])

    msg = InboundMessage(channel="ch", sender_id="u1", chat_id="id", content="hi")
    result = await loop._process_message(msg)

    assert result is None

    outbound: list[OutboundMessage] = []
    while not bus.outbound.empty():
        outbound.append(bus.outbound.get_nowait())

    hints = [m.content for m in outbound]
    assert any("message" in h for h in hints)
    assert all("read_file" not in h for h in hints)


async def test_retry_does_not_add_interim_text_to_context(tmp_path) -> None:
    """Interim text before retry must NOT be added to message history.

    Adding it prefills the assistant role which some providers reject.
    The model gets a clean second chance with the original context.
    """
    from nanobot.providers.base import LLMResponse

    loop = _make_loop(tmp_path)

    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.name = "read_file"
    tool_call.arguments = {"path": "/tmp/test"}

    interim_response = LLMResponse(content="Let me think about this.", tool_calls=[])
    tool_response = LLMResponse(content="", tool_calls=[tool_call])
    final_response = LLMResponse(content="Done!", tool_calls=[])

    call_messages: list[list] = []

    async def _chat(messages, **kwargs):
        call_messages.append(list(messages))
        responses = [interim_response, tool_response, final_response]
        return responses[len(call_messages) - 1]

    loop.provider.chat = _chat
    loop.tools.execute = AsyncMock(return_value="file content")
    loop.tools.get_definitions = MagicMock(return_value=[])

    messages = [{"role": "user", "content": "read the file"}]
    content, _ = await loop._run_agent_loop(messages)

    # Second call (retry) must receive the SAME messages as the first call
    assert call_messages[1] == call_messages[0], (
        "Retry must not inject interim assistant message into context"
    )
    assert content == "Done!"


async def test_matrix_progress_tool_hint_filter_enabled_suppresses_hint(tmp_path) -> None:
    """Matrix can optionally suppress pure tool-hint progress messages."""
    from nanobot.bus.events import InboundMessage
    from nanobot.bus.queue import MessageBus
    from nanobot.providers.base import LLMResponse

    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    loop = AgentLoop(bus=bus, provider=provider, workspace=tmp_path, model="test-model")

    tool_call = MagicMock()
    tool_call.id = "tc-m1"
    tool_call.name = "exec"
    tool_call.arguments = {"command": "ls"}

    loop.provider.chat = AsyncMock(
        side_effect=[
            LLMResponse(content="", tool_calls=[tool_call]),
            LLMResponse(content="Done!", tool_calls=[]),
        ]
    )
    loop.tools.execute = AsyncMock(return_value="ok")
    loop.tools.get_definitions = MagicMock(return_value=[])

    msg = InboundMessage(
        channel="matrix",
        sender_id="u1",
        chat_id="!room:example.org",
        content="list files",
        metadata={"matrix_filter_progress_tool_hints": True},
    )

    result = await loop._process_message(msg)
    assert result is not None
    assert result.content == "Done!"
    assert bus.outbound.empty()


async def test_matrix_progress_tool_hint_filter_disabled_keeps_hint(tmp_path) -> None:
    """Without the matrix flag, formatted tool-hint progress is still sent."""
    from nanobot.bus.events import InboundMessage
    from nanobot.bus.queue import MessageBus
    from nanobot.providers.base import LLMResponse

    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    loop = AgentLoop(bus=bus, provider=provider, workspace=tmp_path, model="test-model")

    tool_call = MagicMock()
    tool_call.id = "tc-m2"
    tool_call.name = "exec"
    tool_call.arguments = {"command": "ls"}

    loop.provider.chat = AsyncMock(
        side_effect=[
            LLMResponse(content="", tool_calls=[tool_call]),
            LLMResponse(content="Done!", tool_calls=[]),
        ]
    )
    loop.tools.execute = AsyncMock(return_value="ok")
    loop.tools.get_definitions = MagicMock(return_value=[])

    msg = InboundMessage(
        channel="matrix",
        sender_id="u1",
        chat_id="!room:example.org",
        content="list files",
        metadata={},
    )

    result = await loop._process_message(msg)
    assert result is not None
    assert result.content == "Done!"
    outbound = await bus.consume_outbound()
    assert outbound.content == 'exec("ls")'
