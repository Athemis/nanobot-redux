"""Tests for MessageBus."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus


@pytest.fixture
def bus():
    return MessageBus()


def make_inbound(**kwargs: Any) -> InboundMessage:
    defaults = dict(channel="matrix", sender_id="u1", chat_id="r1", content="hi")
    return InboundMessage(**{**defaults, **kwargs})


def make_outbound(**kwargs: Any) -> OutboundMessage:
    defaults = dict(channel="matrix", chat_id="r1", content="reply")
    return OutboundMessage(**{**defaults, **kwargs})


@pytest.mark.asyncio
async def test_publish_and_consume_inbound(bus):
    msg = make_inbound()
    await bus.publish_inbound(msg)
    result = await bus.consume_inbound()
    assert result == msg


@pytest.mark.asyncio
async def test_publish_and_consume_outbound(bus):
    msg = make_outbound()
    await bus.publish_outbound(msg)
    result = await bus.consume_outbound()
    assert result == msg


@pytest.mark.asyncio
async def test_inbound_size(bus):
    assert bus.inbound_size == 0
    await bus.publish_inbound(make_inbound())
    assert bus.inbound_size == 1


@pytest.mark.asyncio
async def test_outbound_size(bus):
    assert bus.outbound_size == 0
    await bus.publish_outbound(make_outbound())
    assert bus.outbound_size == 1
