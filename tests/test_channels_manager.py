"""Tests for ChannelManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.manager import ChannelManager
from nanobot.config.schema import Config


def make_config(matrix_enabled=False, email_enabled=False):
    cfg = MagicMock(spec=Config)
    cfg.channels = MagicMock()
    cfg.channels.matrix = MagicMock()
    cfg.channels.matrix.enabled = matrix_enabled
    cfg.channels.email = MagicMock()
    cfg.channels.email.enabled = email_enabled
    cfg.tools = MagicMock()
    cfg.tools.restrict_to_workspace = False
    cfg.workspace_path = None
    return cfg


@pytest.fixture
def bus():
    b = MagicMock(spec=MessageBus)
    b.consume_outbound = AsyncMock()
    b.publish_inbound = AsyncMock()
    return b


def test_init_no_channels_enabled(bus):
    cfg = make_config()
    mgr = ChannelManager(cfg, bus)
    assert mgr.channels == {}
    assert mgr.enabled_channels == []


def test_get_channel_returns_none_for_unknown(bus):
    mgr = ChannelManager(make_config(), bus)
    assert mgr.get_channel("matrix") is None


def test_get_status_empty(bus):
    mgr = ChannelManager(make_config(), bus)
    assert mgr.get_status() == {}


def test_enabled_channels_empty(bus):
    mgr = ChannelManager(make_config(), bus)
    assert mgr.enabled_channels == []


@pytest.mark.asyncio
async def test_start_all_no_channels(bus):
    mgr = ChannelManager(make_config(), bus)
    await mgr.start_all()


@pytest.mark.asyncio
async def test_stop_all_no_channels_no_error(bus):
    mgr = ChannelManager(make_config(), bus)
    await mgr.stop_all()


@pytest.mark.asyncio
async def test_stop_all_cancels_dispatch_task(bus):
    mgr = ChannelManager(make_config(), bus)
    mgr._dispatch_task = asyncio.create_task(asyncio.sleep(9999))
    await mgr.stop_all()
    assert mgr._dispatch_task.cancelled() or mgr._dispatch_task.done()


@pytest.mark.asyncio
async def test_start_channel_logs_error_on_exception(bus):
    mgr = ChannelManager(make_config(), bus)
    fake_channel = MagicMock()
    fake_channel.start = AsyncMock(side_effect=RuntimeError("connect failed"))
    await mgr._start_channel("matrix", fake_channel)


def test_get_status_with_channels(bus):
    mgr = ChannelManager(make_config(), bus)
    fake_channel = MagicMock()
    fake_channel.is_running = True
    mgr.channels["matrix"] = fake_channel
    status = mgr.get_status()
    assert "matrix" in status
    assert status["matrix"]["running"] is True


@pytest.mark.asyncio
async def test_dispatch_outbound_routes_to_channel(bus):
    mgr = ChannelManager(make_config(), bus)
    fake_channel = MagicMock()
    fake_channel.send = AsyncMock()
    mgr.channels["matrix"] = fake_channel

    msg = OutboundMessage(channel="matrix", chat_id="r1", content="hi")
    call_count = 0

    async def side_effect():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return msg
        await asyncio.sleep(9999)

    bus.consume_outbound = side_effect

    task = asyncio.create_task(mgr._dispatch_outbound())
    await asyncio.sleep(0.05)
    task.cancel()

    fake_channel.send.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_dispatch_outbound_unknown_channel(bus):
    mgr = ChannelManager(make_config(), bus)
    msg = OutboundMessage(channel="ghost", chat_id="r1", content="hi")
    call_count = 0

    async def side_effect():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return msg
        await asyncio.sleep(9999)

    bus.consume_outbound = side_effect
    task = asyncio.create_task(mgr._dispatch_outbound())
    await asyncio.sleep(0.05)
    task.cancel()
