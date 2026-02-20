import pytest

from nanobot.agent.tools.message import MessageTool
from nanobot.bus.events import OutboundMessage


@pytest.mark.asyncio
async def test_message_tool_sends_media_paths_with_default_context() -> None:
    sent: list[OutboundMessage] = []

    async def _send(msg: OutboundMessage) -> None:
        sent.append(msg)

    tool = MessageTool(
        send_callback=_send,
        default_channel="test-channel",
        default_chat_id="!room:example.org",
    )

    result = await tool.execute(
        content="Here is the file.",
        media=[" /tmp/test.txt ", "", "   ", "/tmp/report.pdf"],
    )

    assert result == "Message sent to test-channel:!room:example.org with 2 attachments"
    assert len(sent) == 1
    assert sent[0].channel == "test-channel"
    assert sent[0].chat_id == "!room:example.org"
    assert sent[0].content == "Here is the file."
    assert sent[0].media == ["/tmp/test.txt", "/tmp/report.pdf"]


@pytest.mark.asyncio
async def test_message_tool_returns_error_when_no_target_context() -> None:
    tool = MessageTool()
    result = await tool.execute(content="test")
    assert result == "Error: No target channel/chat specified"


@pytest.mark.asyncio
async def test_message_tool_success_without_media_does_not_append_attachment_count() -> None:
    sent: list[OutboundMessage] = []

    async def _send(msg: OutboundMessage) -> None:
        sent.append(msg)

    tool = MessageTool(
        send_callback=_send,
        default_channel="matrix",
        default_chat_id="!room:example.org",
    )

    result = await tool.execute(content="hello")

    assert result == "Message sent to matrix:!room:example.org"
    assert len(sent) == 1
    assert sent[0].media == []


@pytest.mark.asyncio
async def test_message_tool_uses_singular_attachment_label_for_one_media_path() -> None:
    sent: list[OutboundMessage] = []

    async def _send(msg: OutboundMessage) -> None:
        sent.append(msg)

    tool = MessageTool(
        send_callback=_send,
        default_channel="matrix",
        default_chat_id="!room:example.org",
    )

    result = await tool.execute(content="hello", media=[" /tmp/one.txt "])

    assert result == "Message sent to matrix:!room:example.org with 1 attachment"
    assert len(sent) == 1
    assert sent[0].media == ["/tmp/one.txt"]


def test_message_tool_has_sent_in_turn_flag() -> None:
    """MessageTool must expose _sent_in_turn and start_turn() for duplicate-reply guard."""
    tool = MessageTool(default_channel="ch", default_chat_id="id")
    assert hasattr(tool, "_sent_in_turn")
    assert tool._sent_in_turn is False
    assert tool.sent_in_turn is False
    assert tool.sent_in_turn_target is None


@pytest.mark.asyncio
async def test_start_turn_resets_sent_flag() -> None:
    """start_turn() must reset _sent_in_turn to False."""
    sent: list[OutboundMessage] = []

    async def _send(msg: OutboundMessage) -> None:
        sent.append(msg)

    tool = MessageTool(send_callback=_send, default_channel="ch", default_chat_id="id")
    await tool.execute(content="hello")
    assert tool._sent_in_turn is True
    assert tool.sent_in_turn_target == ("ch", "id")
    tool.start_turn()
    assert tool._sent_in_turn is False
    assert tool.sent_in_turn_target is None


@pytest.mark.asyncio
async def test_execute_sets_sent_in_turn() -> None:
    """execute() must set _sent_in_turn=True after a successful send."""
    sent: list[OutboundMessage] = []

    async def _send(msg: OutboundMessage) -> None:
        sent.append(msg)

    tool = MessageTool(send_callback=_send, default_channel="ch", default_chat_id="id")
    assert tool._sent_in_turn is False
    await tool.execute(content="hi")
    assert tool._sent_in_turn is True
