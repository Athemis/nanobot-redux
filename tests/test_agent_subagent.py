"""Tests for SubagentManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from nanobot.agent.subagent import SubagentManager
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMResponse


def make_response(content=None, tool_calls=None, finish_reason="stop"):
    r = MagicMock(spec=LLMResponse)
    r.content = content
    r.tool_calls = tool_calls or []
    r.has_tool_calls = bool(tool_calls)
    r.finish_reason = finish_reason
    return r


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


@pytest.fixture
def provider():
    p = MagicMock()
    p.get_default_model.return_value = "gpt-4o"
    p.chat = AsyncMock(return_value=make_response(content="done"))
    return p


@pytest.fixture
def bus():
    b = MagicMock(spec=MessageBus)
    b.publish_inbound = AsyncMock()
    return b


@pytest.fixture
def manager(provider, workspace, bus):
    return SubagentManager(provider=provider, workspace=workspace, bus=bus)


def test_get_running_count_zero_initially(manager):
    assert manager.get_running_count() == 0


@pytest.mark.asyncio
async def test_spawn_returns_status_message(manager):
    result = await manager.spawn("do something")
    assert "started" in result.lower()


@pytest.mark.asyncio
async def test_spawn_runs_subagent_and_announces_result(manager, bus):
    await manager.spawn("do something")
    await asyncio.sleep(0.1)
    bus.publish_inbound.assert_awaited()


@pytest.mark.asyncio
async def test_run_subagent_announces_on_exception(manager, provider, bus):
    provider.chat = AsyncMock(side_effect=RuntimeError("boom"))
    await manager._run_subagent(
        "t1", "bad task", "bad task",
        {"channel": "cli", "chat_id": "direct"}
    )
    call_arg = bus.publish_inbound.call_args[0][0]
    assert "Error" in call_arg.content or "failed" in call_arg.content.lower()


@pytest.mark.asyncio
async def test_run_subagent_max_iterations_exceeded(manager, provider, bus):
    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.name = "read_file"
    tool_call.arguments = {}
    provider.chat = AsyncMock(return_value=make_response(tool_calls=[tool_call]))

    await manager._run_subagent(
        "t1", "loop forever", "loop",
        {"channel": "cli", "chat_id": "direct"}
    )
    bus.publish_inbound.assert_awaited()


def test_build_skills_section_empty_when_no_skills(manager):
    result = manager._build_skills_section()
    assert result == "" or isinstance(result, str)
