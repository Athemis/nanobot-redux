"""Tests for BaseChannel."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel


class ConcreteChannel(BaseChannel):
    name = "test"

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: object) -> None:
        pass


@pytest.fixture
def bus():
    b = MagicMock(spec=MessageBus)
    b.publish_inbound = AsyncMock()
    return b


@pytest.fixture
def channel(bus):
    cfg = MagicMock()
    cfg.allow_from = []
    return ConcreteChannel(cfg, bus)


@pytest.mark.asyncio
async def test_start_sets_running(channel):
    await channel.start()
    assert channel.is_running is True


@pytest.mark.asyncio
async def test_stop_clears_running(channel):
    await channel.start()
    await channel.stop()
    assert channel.is_running is False


def test_is_allowed_empty_list_allows_all(channel):
    assert channel.is_allowed("anyone") is True


def test_is_allowed_with_matching_sender(channel):
    channel.config.allow_from = ["alice", "bob"]
    assert channel.is_allowed("alice") is True


def test_is_allowed_with_unknown_sender(channel):
    channel.config.allow_from = ["alice"]
    assert channel.is_allowed("charlie") is False


def test_is_allowed_pipe_separated_match(channel):
    channel.config.allow_from = ["alice"]
    assert channel.is_allowed("device|alice") is True


def test_is_allowed_pipe_separated_no_match(channel):
    channel.config.allow_from = ["alice"]
    assert channel.is_allowed("device|bob") is False


@pytest.mark.asyncio
async def test_handle_message_publishes_when_allowed(channel, bus):
    channel.config.allow_from = []
    await channel._handle_message("u1", "r1", "hello")
    bus.publish_inbound.assert_awaited_once()
    call_arg = bus.publish_inbound.call_args[0][0]
    assert isinstance(call_arg, InboundMessage)
    assert call_arg.content == "hello"


@pytest.mark.asyncio
async def test_handle_message_blocked_when_denied(channel, bus):
    channel.config.allow_from = ["alice"]
    await channel._handle_message("eve", "r1", "hack")
    bus.publish_inbound.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_passes_media_and_metadata(channel, bus):
    await channel._handle_message("u1", "r1", "hi", media=["img.png"], metadata={"k": "v"})
    msg = bus.publish_inbound.call_args[0][0]
    assert msg.media == ["img.png"]
    assert msg.metadata == {"k": "v"}


@pytest.mark.asyncio
async def test_handle_message_blocked_logs_safely_with_curly_braces(channel, bus) -> None:
    """Access-denied warning must not raise KeyError when sender_id has curly braces."""
    channel.config.allow_from = ["alice"]
    # f-string logger raises KeyError if sender contains "{" or "}"
    await channel._handle_message("{evil}", "r1", "hack")
    bus.publish_inbound.assert_not_awaited()
