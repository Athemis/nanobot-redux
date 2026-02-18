"""Tests for MessageBus."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus


@pytest.fixture
def bus():
    return MessageBus()


def make_inbound(**kwargs):
    defaults = dict(channel="matrix", sender_id="u1", chat_id="r1", content="hi")
    return InboundMessage(**{**defaults, **kwargs})


def make_outbound(**kwargs):
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


def test_subscribe_outbound_registers_callback(bus):
    cb = AsyncMock()
    bus.subscribe_outbound("matrix", cb)
    assert cb in bus._outbound_subscribers["matrix"]


def test_subscribe_outbound_multiple_channels(bus):
    cb1 = AsyncMock()
    cb2 = AsyncMock()
    bus.subscribe_outbound("matrix", cb1)
    bus.subscribe_outbound("email", cb2)
    assert cb1 in bus._outbound_subscribers["matrix"]
    assert cb2 in bus._outbound_subscribers["email"]


@pytest.mark.asyncio
async def test_dispatch_outbound_calls_subscribers(bus):
    received = []

    async def handler(msg):
        received.append(msg)

    bus.subscribe_outbound("matrix", handler)
    msg = make_outbound(channel="matrix")
    await bus.publish_outbound(msg)

    task = asyncio.create_task(bus.dispatch_outbound())
    await asyncio.sleep(0.05)
    bus.stop()
    await asyncio.sleep(0.05)
    task.cancel()

    assert received == [msg]


@pytest.mark.asyncio
async def test_dispatch_outbound_logs_subscriber_error(bus):
    async def failing_handler(_msg):
        raise RuntimeError("boom")

    bus.subscribe_outbound("matrix", failing_handler)
    await bus.publish_outbound(make_outbound(channel="matrix"))

    task = asyncio.create_task(bus.dispatch_outbound())
    await asyncio.sleep(0.05)
    bus.stop()
    task.cancel()
    # No exception should propagate


@pytest.mark.asyncio
async def test_dispatch_outbound_unknown_channel_is_silent(bus):
    await bus.publish_outbound(make_outbound(channel="unknown"))
    task = asyncio.create_task(bus.dispatch_outbound())
    await asyncio.sleep(0.05)
    bus.stop()
    task.cancel()


def test_stop_sets_running_false(bus):
    bus._running = True
    bus.stop()
    assert bus._running is False
