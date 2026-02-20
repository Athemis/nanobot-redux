"""Tests for MCPToolWrapper and connect_mcp_servers."""

import asyncio
from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.agent.tools.mcp import MCPToolWrapper
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.bus.queue import MessageBus


def make_tool_def(name="echo", description="Echo tool", schema=None):
    td = MagicMock()
    td.name = name
    td.description = description
    td.inputSchema = schema or {"type": "object", "properties": {}}
    return td


@pytest.fixture
def session():
    s = MagicMock()
    s.call_tool = AsyncMock()
    return s


def test_name_is_namespaced(session):
    w = MCPToolWrapper(session, "myserver", make_tool_def("echo"))
    assert w.name == "mcp_myserver_echo"


def test_description_from_tool_def(session):
    w = MCPToolWrapper(session, "srv", make_tool_def(description="Does X"))
    assert w.description == "Does X"


def test_description_falls_back_to_name_when_none(session):
    td = make_tool_def(name="mytool", description=None)
    w = MCPToolWrapper(session, "srv", td)
    assert w.description == "mytool"


def test_parameters_from_tool_def(session):
    schema = {"type": "object", "properties": {"x": {"type": "string"}}}
    w = MCPToolWrapper(session, "srv", make_tool_def(schema=schema))
    assert w.parameters == schema


@pytest.mark.asyncio
async def test_execute_returns_no_output_when_empty(session):
    session.call_tool.return_value = MagicMock(content=[])
    w = MCPToolWrapper(session, "srv", make_tool_def())
    result = await w.execute()
    assert result == "(no output)"


@pytest.mark.asyncio
async def test_connect_mcp_servers_skips_when_no_command_or_url():
    from nanobot.agent.tools.mcp import connect_mcp_servers

    registry = ToolRegistry()
    cfg = MagicMock()
    cfg.command = None
    cfg.url = None

    async with AsyncExitStack() as stack:
        await connect_mcp_servers({"myserver": cfg}, registry, stack)

    assert registry.get_definitions() == []


@pytest.mark.asyncio
async def test_connect_mcp_servers_logs_error_on_failure():
    from nanobot.agent.tools.mcp import connect_mcp_servers

    registry = ToolRegistry()
    cfg = MagicMock()
    cfg.command = "nonexistent-binary"
    cfg.args = []
    cfg.env = None

    async with AsyncExitStack() as stack:
        with patch("mcp.client.stdio.stdio_client", side_effect=FileNotFoundError("not found")):
            await connect_mcp_servers({"srv": cfg}, registry, stack)

    # Registry should remain empty after failed connection
    assert registry.get_definitions() == []


@pytest.mark.asyncio
async def test_connect_mcp_retries_after_failure(tmp_path) -> None:
    """If MCP connection fails, _mcp_connected stays False so next call retries."""
    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"

    loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=tmp_path,
        model="test-model",
        mcp_servers={"srv": MagicMock(command="fake-server", args=[], env=None, url=None)},
    )

    with patch(
        "nanobot.agent.tools.mcp.connect_mcp_servers",
        side_effect=RuntimeError("connection refused"),
    ):
        await loop._connect_mcp()

    # After failure: _mcp_connected must be False so next message retries
    assert not loop._mcp_connected


@pytest.mark.asyncio
async def test_connect_mcp_concurrent_guard(tmp_path) -> None:
    """Concurrent callers must not race through _connect_mcp."""
    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"

    connect_calls = []

    async def slow_connect(servers, registry, stack):
        connect_calls.append(1)
        await asyncio.sleep(0)  # yield to let concurrent call attempt

    loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=tmp_path,
        model="test-model",
        mcp_servers={"srv": MagicMock(command="fake-server", args=[], env=None, url=None)},
    )

    with patch("nanobot.agent.tools.mcp.connect_mcp_servers", side_effect=slow_connect):
        await asyncio.gather(loop._connect_mcp(), loop._connect_mcp())

    # connect_mcp_servers must only be called once (concurrent guard works)
    assert len(connect_calls) == 1
    # And the connection must have succeeded
    assert loop._mcp_connected is True
