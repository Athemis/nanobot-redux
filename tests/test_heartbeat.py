"""Tests for HeartbeatService."""

from unittest.mock import AsyncMock

import pytest

from nanobot.heartbeat.service import (
    HEARTBEAT_OK_TOKEN,
    HEARTBEAT_PROMPT,
    HeartbeatService,
    _is_heartbeat_empty,
)

# ── _is_heartbeat_empty ───────────────────────────────────────────────────────


def test_empty_string_is_empty():
    assert _is_heartbeat_empty("") is True


def test_none_is_empty():
    assert _is_heartbeat_empty(None) is True


def test_only_headers_is_empty():
    assert _is_heartbeat_empty("# Title\n## Sub") is True


def test_only_html_comments_is_empty():
    assert _is_heartbeat_empty("<!-- comment -->") is True


def test_only_checkboxes_is_empty():
    assert _is_heartbeat_empty("- [ ]\n* [x]") is True


def test_real_content_is_not_empty():
    assert _is_heartbeat_empty("Check the logs") is False


# ── HeartbeatService ──────────────────────────────────────────────────────────


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


def test_heartbeat_file_path(workspace):
    svc = HeartbeatService(workspace)
    assert svc.heartbeat_file == workspace / "HEARTBEAT.md"


def test_read_heartbeat_file_returns_none_when_missing(workspace):
    svc = HeartbeatService(workspace)
    assert svc._read_heartbeat_file() is None


def test_read_heartbeat_file_returns_content(workspace):
    svc = HeartbeatService(workspace)
    (workspace / "HEARTBEAT.md").write_text("do stuff")
    assert svc._read_heartbeat_file() == "do stuff"


@pytest.mark.asyncio
async def test_start_disabled_does_nothing(workspace):
    svc = HeartbeatService(workspace, enabled=False)
    await svc.start()
    assert svc._running is False
    assert svc._task is None


@pytest.mark.asyncio
async def test_start_creates_task(workspace):
    svc = HeartbeatService(workspace, interval_s=9999)
    await svc.start()
    assert svc._running is True
    assert svc._task is not None
    svc.stop()


@pytest.mark.asyncio
async def test_stop_cancels_task(workspace):
    svc = HeartbeatService(workspace, interval_s=9999)
    await svc.start()
    svc.stop()
    assert svc._running is False
    assert svc._task is None


@pytest.mark.asyncio
async def test_tick_skips_when_heartbeat_empty(workspace):
    cb = AsyncMock()
    svc = HeartbeatService(workspace, on_heartbeat=cb)
    await svc._tick()
    cb.assert_not_awaited()


@pytest.mark.asyncio
async def test_tick_calls_callback_when_content_present(workspace):
    cb = AsyncMock(return_value="did things")
    svc = HeartbeatService(workspace, on_heartbeat=cb)
    (workspace / "HEARTBEAT.md").write_text("check the logs")
    await svc._tick()
    cb.assert_awaited_once_with(HEARTBEAT_PROMPT)


@pytest.mark.asyncio
async def test_tick_logs_ok_when_heartbeat_ok_returned(workspace):
    cb = AsyncMock(return_value=HEARTBEAT_OK_TOKEN)
    svc = HeartbeatService(workspace, on_heartbeat=cb)
    (workspace / "HEARTBEAT.md").write_text("check the logs")
    await svc._tick()


@pytest.mark.asyncio
async def test_tick_handles_callback_exception(workspace):
    cb = AsyncMock(side_effect=RuntimeError("agent crashed"))
    svc = HeartbeatService(workspace, on_heartbeat=cb)
    (workspace / "HEARTBEAT.md").write_text("check the logs")
    await svc._tick()


@pytest.mark.asyncio
async def test_trigger_now_calls_callback(workspace):
    cb = AsyncMock(return_value="result")
    svc = HeartbeatService(workspace, on_heartbeat=cb)
    result = await svc.trigger_now()
    assert result == "result"


@pytest.mark.asyncio
async def test_trigger_now_returns_none_when_no_callback(workspace):
    svc = HeartbeatService(workspace)
    result = await svc.trigger_now()
    assert result is None
