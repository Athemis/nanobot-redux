import builtins
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from nanobot.cli.commands import app

runner = CliRunner()


@pytest.fixture
def mock_paths():
    """Mock config/workspace paths for test isolation."""
    with (
        patch("nanobot.config.loader.get_config_path") as mock_cp,
        patch("nanobot.config.loader.save_config") as mock_sc,
        patch("nanobot.config.loader.load_config"),
        patch("nanobot.utils.helpers.get_workspace_path") as mock_ws,
    ):
        base_dir = Path("./test_onboard_data")
        if base_dir.exists():
            shutil.rmtree(base_dir)
        base_dir.mkdir()

        config_file = base_dir / "config.json"
        workspace_dir = base_dir / "workspace"

        mock_cp.return_value = config_file
        mock_ws.return_value = workspace_dir
        mock_sc.side_effect = lambda config: config_file.write_text("{}")

        yield config_file, workspace_dir

        if base_dir.exists():
            shutil.rmtree(base_dir)


def test_onboard_fresh_install(mock_paths):
    """No existing config — should create from scratch."""
    config_file, workspace_dir = mock_paths

    result = runner.invoke(app, ["onboard"])

    assert result.exit_code == 0
    assert "Created config" in result.stdout
    assert "Created workspace" in result.stdout
    assert "nanobot is ready" in result.stdout
    assert config_file.exists()
    assert (workspace_dir / "AGENTS.md").exists()
    assert (workspace_dir / "memory" / "MEMORY.md").exists()


def test_onboard_existing_config_refresh(mock_paths):
    """Config exists, user declines overwrite — should refresh (load-merge-save)."""
    config_file, workspace_dir = mock_paths
    config_file.write_text('{"existing": true}')

    result = runner.invoke(app, ["onboard"], input="n\n")

    assert result.exit_code == 0
    assert "Config already exists" in result.stdout
    assert "existing values preserved" in result.stdout
    assert workspace_dir.exists()
    assert (workspace_dir / "AGENTS.md").exists()


def test_onboard_existing_config_overwrite(mock_paths):
    """Config exists, user confirms overwrite — should reset to defaults."""
    config_file, workspace_dir = mock_paths
    config_file.write_text('{"existing": true}')

    result = runner.invoke(app, ["onboard"], input="y\n")

    assert result.exit_code == 0
    assert "Config already exists" in result.stdout
    assert "Config reset to defaults" in result.stdout
    assert workspace_dir.exists()


def test_onboard_existing_workspace_safe_create(mock_paths):
    """Workspace exists — should not recreate, but still add missing templates."""
    config_file, workspace_dir = mock_paths
    workspace_dir.mkdir(parents=True)
    config_file.write_text("{}")

    result = runner.invoke(app, ["onboard"], input="n\n")

    assert result.exit_code == 0
    assert "Created workspace" not in result.stdout
    assert "Created AGENTS.md" in result.stdout
    assert (workspace_dir / "AGENTS.md").exists()


# ============================================================================
# Version flag
# ============================================================================


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "nanobot" in result.stdout


# ============================================================================
# Internal helper functions
# ============================================================================


def test_print_agent_response_plain():
    from nanobot.cli.commands import _print_agent_response

    _print_agent_response("hello world", render_markdown=False)


def test_print_agent_response_markdown():
    from nanobot.cli.commands import _print_agent_response

    _print_agent_response("**bold**", render_markdown=True)


def test_print_agent_response_empty():
    from nanobot.cli.commands import _print_agent_response

    _print_agent_response("", render_markdown=False)


def test_is_exit_command_true():
    from nanobot.cli.commands import _is_exit_command

    assert _is_exit_command("exit") is True
    assert _is_exit_command("quit") is True
    assert _is_exit_command("/exit") is True
    assert _is_exit_command("/quit") is True
    assert _is_exit_command(":q") is True
    assert _is_exit_command("EXIT") is True


def test_is_exit_command_false():
    from nanobot.cli.commands import _is_exit_command

    assert _is_exit_command("hello") is False
    assert _is_exit_command("") is False
    assert _is_exit_command("ex it") is False


def test_read_interactive_input_async_no_session():
    import asyncio

    import nanobot.cli.commands as cmd_mod
    from nanobot.cli.commands import _read_interactive_input_async

    original = cmd_mod._PROMPT_SESSION
    cmd_mod._PROMPT_SESSION = None
    try:
        with pytest.raises(RuntimeError, match="Call _init_prompt_session"):
            asyncio.run(_read_interactive_input_async())
    finally:
        cmd_mod._PROMPT_SESSION = original


# ============================================================================
# channels status command
# ============================================================================


def test_channels_status(monkeypatch, tmp_path):
    from nanobot.config.schema import Config

    monkeypatch.setattr("nanobot.config.loader.get_config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr("nanobot.config.loader.load_config", lambda *a, **kw: Config())
    result = runner.invoke(app, ["channels", "status"])
    assert result.exit_code == 0
    assert "Matrix" in result.stdout
    assert "Email" in result.stdout


# ============================================================================
# cron list command
# ============================================================================


def test_cron_list_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "list"])
    assert result.exit_code == 0
    assert "No scheduled jobs" in result.stdout


def test_cron_list_with_jobs(monkeypatch, tmp_path):
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule

    store = tmp_path / "cron" / "jobs.json"
    svc = CronService(store)
    svc.add_job("test job", CronSchedule(kind="every", every_ms=60000), "hello")

    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "list"])
    assert result.exit_code == 0
    assert "test job" in result.stdout


def test_cron_list_with_cron_expr_job(monkeypatch, tmp_path):
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule

    store = tmp_path / "cron" / "jobs.json"
    svc = CronService(store)
    svc.add_job("daily job", CronSchedule(kind="cron", expr="0 9 * * *", tz="UTC"), "good morning")

    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "list"])
    assert result.exit_code == 0
    assert "daily job" in result.stdout


def test_cron_list_all_flag(monkeypatch, tmp_path):
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule

    store = tmp_path / "cron" / "jobs.json"
    svc = CronService(store)
    job = svc.add_job("disabled job", CronSchedule(kind="every", every_ms=60000), "run me")
    svc.enable_job(job.id, enabled=False)

    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)

    # Without --all, disabled jobs are hidden
    result = runner.invoke(app, ["cron", "list"])
    assert result.exit_code == 0
    assert "No scheduled jobs" in result.stdout

    # With --all, disabled jobs appear
    result = runner.invoke(app, ["cron", "list", "--all"])
    assert result.exit_code == 0
    assert "disabled job" in result.stdout


# ============================================================================
# cron add command
# ============================================================================


def test_cron_add_every(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "add", "--name", "x", "--message", "hi", "--every", "60"])
    assert result.exit_code == 0
    assert "Added job" in result.stdout


def test_cron_add_cron_expr(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(
        app,
        ["cron", "add", "--name", "daily", "--message", "morning", "--cron", "0 9 * * *"],
    )
    assert result.exit_code == 0
    assert "Added job" in result.stdout


def test_cron_add_cron_expr_with_tz(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(
        app,
        [
            "cron",
            "add",
            "--name",
            "tz job",
            "--message",
            "hi",
            "--cron",
            "0 9 * * *",
            "--tz",
            "UTC",
        ],
    )
    assert result.exit_code == 0
    assert "Added job" in result.stdout


def test_cron_add_tz_without_cron(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(
        app,
        ["cron", "add", "--name", "x", "--message", "hi", "--every", "60", "--tz", "UTC"],
    )
    assert result.exit_code == 1


def test_cron_add_at(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(
        app,
        ["cron", "add", "--name", "once", "--message", "run once", "--at", "2030-01-01T10:00:00"],
    )
    assert result.exit_code == 0
    assert "Added job" in result.stdout


def test_cron_add_no_schedule(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "add", "--name", "x", "--message", "hi"])
    assert result.exit_code == 1
    assert "Must specify" in result.stdout


# ============================================================================
# cron remove command
# ============================================================================


def test_cron_remove_found(monkeypatch, tmp_path):
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule

    store = tmp_path / "cron" / "jobs.json"
    svc = CronService(store)
    job = svc.add_job("to remove", CronSchedule(kind="every", every_ms=60000), "bye")

    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "remove", job.id])
    assert result.exit_code == 0
    assert "Removed job" in result.stdout


def test_cron_remove_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "remove", "nonexistent-id"])
    assert result.exit_code == 0
    assert "not found" in result.stdout


# ============================================================================
# cron enable/disable command
# ============================================================================


def test_cron_enable_found(monkeypatch, tmp_path):
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule

    store = tmp_path / "cron" / "jobs.json"
    svc = CronService(store)
    job = svc.add_job("toggle me", CronSchedule(kind="every", every_ms=60000), "hello")
    svc.enable_job(job.id, enabled=False)

    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "enable", job.id])
    assert result.exit_code == 0
    assert "enabled" in result.stdout


def test_cron_disable_found(monkeypatch, tmp_path):
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule

    store = tmp_path / "cron" / "jobs.json"
    svc = CronService(store)
    job = svc.add_job("disable me", CronSchedule(kind="every", every_ms=60000), "hello")

    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "enable", job.id, "--disable"])
    assert result.exit_code == 0
    assert "disabled" in result.stdout


def test_cron_enable_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cron", "enable", "nonexistent"])
    assert result.exit_code == 0
    assert "not found" in result.stdout


# ============================================================================
# cron run command
# ============================================================================


def test_cron_run_success(monkeypatch, tmp_path) -> None:
    from unittest.mock import AsyncMock, MagicMock

    from nanobot.config.schema import Config
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule

    store = tmp_path / "cron" / "jobs.json"
    svc = CronService(store)
    job = svc.add_job("runnable", CronSchedule(kind="every", every_ms=60000), "do it")

    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.config.loader.load_config", lambda *a, **kw: Config())
    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(
        return_value=MagicMock(content="done", tool_calls=[], has_tool_calls=False)
    )
    monkeypatch.setattr("nanobot.cli.commands._make_provider", lambda cfg: mock_provider)
    result = runner.invoke(app, ["cron", "run", job.id])
    assert result.exit_code == 0
    assert "Job executed" in result.stdout


def test_cron_run_not_found(monkeypatch, tmp_path) -> None:
    from unittest.mock import MagicMock

    from nanobot.config.schema import Config

    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.config.loader.load_config", lambda *a, **kw: Config())
    monkeypatch.setattr("nanobot.cli.commands._make_provider", lambda cfg: MagicMock())
    result = runner.invoke(app, ["cron", "run", "bad-id"])
    assert result.exit_code == 0
    assert "Failed to run job" in result.stdout


def test_cron_run_disabled_without_force(monkeypatch, tmp_path) -> None:
    from unittest.mock import MagicMock

    from nanobot.config.schema import Config
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronSchedule

    store = tmp_path / "cron" / "jobs.json"
    svc = CronService(store)
    job = svc.add_job("disabled", CronSchedule(kind="every", every_ms=60000), "hi")
    svc.enable_job(job.id, enabled=False)

    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.config.loader.load_config", lambda *a, **kw: Config())
    monkeypatch.setattr("nanobot.cli.commands._make_provider", lambda cfg: MagicMock())
    result = runner.invoke(app, ["cron", "run", job.id])
    assert result.exit_code == 0
    assert "Failed to run job" in result.stdout


# ============================================================================
# status command
# ============================================================================


def test_status_no_config(monkeypatch, tmp_path):
    from nanobot.config.schema import Config

    monkeypatch.setattr("nanobot.config.loader.get_config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr("nanobot.config.loader.load_config", lambda *a, **kw: Config())
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Status" in result.stdout


def test_status_with_config(monkeypatch, tmp_path):
    from nanobot.config.schema import Config

    config_path = tmp_path / "config.json"
    config_path.write_text("{}")
    monkeypatch.setattr("nanobot.config.loader.get_config_path", lambda: config_path)
    monkeypatch.setattr("nanobot.config.loader.load_config", lambda *a, **kw: Config())
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Model" in result.stdout


# ============================================================================
# _make_provider error paths
# ============================================================================


def test_make_provider_bedrock_exits():
    import click

    from nanobot.cli.commands import _make_provider
    from nanobot.config.schema import Config

    config = Config()
    config.agents.defaults.model = "bedrock/anthropic.claude-3"
    with pytest.raises(click.exceptions.Exit):
        _make_provider(config)


def test_make_provider_no_api_key_exits():
    import click

    from nanobot.cli.commands import _make_provider
    from nanobot.config.schema import Config

    config = Config()
    config.agents.defaults.model = "openai/gpt-4o"
    # providers.openai has empty api_key by default — no key configured so Exit(1)
    with pytest.raises(click.exceptions.Exit):
        _make_provider(config)


# ============================================================================
# provider login command
# ============================================================================


def test_provider_login_unknown():
    result = runner.invoke(app, ["provider", "login", "unknown-provider"])
    assert result.exit_code == 1
    assert "Unknown OAuth provider" in result.stdout


def test_provider_login_openai_codex_import_error(monkeypatch):
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "oauth_cli_kit":
            raise ImportError("no module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    result = runner.invoke(app, ["provider", "login", "openai-codex"])
    assert result.exit_code == 1
    assert "not installed" in result.stdout


# ============================================================================
# Interactive CLI bus routing (upstream PR #908)
# ============================================================================


async def test_run_once_uses_thinking_ctx(tmp_path) -> None:
    """run_once must wrap process_direct in _thinking_ctx so the spinner appears.

    Upstream 7279ff0: single-message mode should also show the thinking spinner.
    This test verifies that the _thinking_ctx context manager is entered when
    running in non-interactive (run_once) mode.

    _thinking_ctx (when logs=False) delegates to console.status(). We spy on
    console.status to detect whether the spinner is entered during run_once.

    Regression detection: if the with _thinking_ctx(): wrapper is absent,
    console.status will never be entered and the assertion fails.
    """
    from contextlib import contextmanager
    from unittest.mock import AsyncMock, MagicMock, patch

    from nanobot.config.schema import Config

    status_entered = []

    @contextmanager
    def _spy_status(*args, **kwargs):
        status_entered.append(args[0] if args else kwargs)
        yield MagicMock()

    captured_coros: list = []

    def _capture_asyncio_run(coro):  # type: ignore[override]
        captured_coros.append(coro)

    import nanobot.cli.commands as cmd_mod

    with (
        patch("nanobot.agent.loop.AgentLoop") as mock_agent_loop_cls,
        patch("nanobot.config.loader.load_config", return_value=Config()),
        patch("nanobot.cli.commands._make_provider", return_value=MagicMock()),
        patch("nanobot.cron.service.CronService", return_value=MagicMock()),
        patch("nanobot.config.loader.get_data_dir", return_value=tmp_path),
        patch("asyncio.run", side_effect=_capture_asyncio_run),
        patch.object(cmd_mod.console, "status", side_effect=_spy_status),
    ):
        mock_loop = MagicMock()
        mock_loop.process_direct = AsyncMock(return_value="Agent reply")
        mock_loop.close_mcp = AsyncMock()
        mock_agent_loop_cls.return_value = mock_loop

        from nanobot.cli.commands import agent

        agent(  # type: ignore[arg-type]
            message="hello", session_id="cli:test", markdown=True, logs=False
        )
        # agent() called asyncio.run(run_once()) — await it while patches are active
        assert len(captured_coros) == 1, "Expected asyncio.run called once for run_once"
        await captured_coros[0]

    assert len(status_entered) == 1, (
        f"Expected console.status (the spinner) to be entered once during run_once, "
        f"got {len(status_entered)}. "
        "The with _thinking_ctx(): wrapper is missing from run_once."
    )


async def test_run_interactive_routes_user_input_through_bus(tmp_path) -> None:
    """run_interactive publishes user input via bus.publish_inbound, not process_direct.

    Upstream PR #908: interactive mode must use the MessageBus so subagent replies
    are delivered correctly. This test exercises the actual run_interactive coroutine
    end-to-end: verifies user message reaches bus.inbound and the agent response
    (from bus.outbound) is displayed.

    Regression detection: if process_direct() were re-introduced, bus.publish_inbound
    would never be called and captured_inbound would stay empty — test fails.
    """
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    from nanobot.bus.events import InboundMessage, OutboundMessage
    from nanobot.bus.queue import MessageBus
    from nanobot.config.schema import Config

    captured_inbound: list[InboundMessage] = []
    real_bus = MessageBus()
    original_publish_inbound = real_bus.publish_inbound

    async def _spy_publish_inbound(msg: InboundMessage) -> None:
        captured_inbound.append(msg)
        await original_publish_inbound(msg)

    real_bus.publish_inbound = _spy_publish_inbound  # type: ignore[method-assign]

    # Shared stop signal so mock stop() can terminate the fake agent run()
    agent_stopped = asyncio.Event()

    # Fake agent: reads inbound message, publishes a response to outbound
    async def _fake_agent_run() -> None:
        try:
            while not agent_stopped.is_set():
                try:
                    inbound = await asyncio.wait_for(real_bus.consume_inbound(), timeout=0.1)
                    await real_bus.publish_outbound(
                        OutboundMessage(
                            channel=inbound.channel,
                            chat_id=inbound.chat_id,
                            content="Mock agent response",
                        )
                    )
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass

    mock_loop = MagicMock()
    mock_loop.run = _fake_agent_run
    mock_loop.stop = lambda: agent_stopped.set()
    mock_loop.close_mcp = AsyncMock()

    printed_responses: list[str] = []
    user_inputs = iter(["Hello agent", "exit"])

    async def _mock_read_input() -> str:
        try:
            return next(user_inputs)
        except StopIteration:
            raise EOFError

    # Capture the coroutine passed to asyncio.run so we can await it ourselves
    captured_coros: list = []

    def _capture_asyncio_run(coro):  # type: ignore[override]
        captured_coros.append(coro)

    with (
        patch("nanobot.bus.queue.MessageBus", return_value=real_bus),
        patch("nanobot.agent.loop.AgentLoop", return_value=mock_loop),
        patch("nanobot.config.loader.load_config", return_value=Config()),
        patch("nanobot.cli.commands._make_provider", return_value=MagicMock()),
        patch("nanobot.cron.service.CronService", return_value=MagicMock()),
        patch("nanobot.config.loader.get_data_dir", return_value=tmp_path),
        patch("nanobot.cli.commands._read_interactive_input_async", side_effect=_mock_read_input),
        patch("nanobot.cli.commands._init_prompt_session"),
        patch("nanobot.cli.commands._flush_pending_tty_input"),
        patch("nanobot.cli.commands._restore_terminal"),
        patch(
            "nanobot.cli.commands._print_agent_response",
            side_effect=lambda r, **kw: printed_responses.append(r),
        ),
        patch("asyncio.run", side_effect=_capture_asyncio_run),
    ):
        from nanobot.cli.commands import agent

        agent(  # type: ignore[arg-type]
            message=None, session_id="cli:test", markdown=True, logs=False
        )
        # agent() called asyncio.run(run_interactive()) — await it while patches are active
        assert len(captured_coros) == 1, "Expected asyncio.run called once for run_interactive"
        await captured_coros[0]

    # User message must have gone through bus.publish_inbound (not process_direct)
    assert len(captured_inbound) == 1, (
        f"Expected 1 inbound via bus.publish_inbound, got {len(captured_inbound)}. "
        "A regression to process_direct() would leave this list empty."
    )
    assert captured_inbound[0].content == "Hello agent"
    assert captured_inbound[0].channel == "cli"

    # Agent response from bus.outbound must be displayed
    assert len(printed_responses) == 1, (
        f"Expected 1 printed response from bus outbound, got {len(printed_responses)}"
    )
    assert printed_responses[0] == "Mock agent response"


async def test_run_interactive_displays_progress_hints_and_final_response(
    tmp_path,
) -> None:
    """Progress messages (_progress=True) shown as hints; final message printed.

    Upstream PR #908: _consume_outbound must route messages with metadata._progress=True
    to dim-text hints and route the final turn response to _print_agent_response.
    """
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    from nanobot.bus.events import OutboundMessage
    from nanobot.bus.queue import MessageBus
    from nanobot.config.schema import Config

    real_bus = MessageBus()
    agent_stopped2 = asyncio.Event()

    async def _fake_agent_run() -> None:
        try:
            while not agent_stopped2.is_set():
                try:
                    inbound = await asyncio.wait_for(real_bus.consume_inbound(), timeout=0.1)
                    # First: a progress hint
                    await real_bus.publish_outbound(
                        OutboundMessage(
                            channel=inbound.channel,
                            chat_id=inbound.chat_id,
                            content="Calling tool: shell",
                            metadata={"_progress": True},
                        )
                    )
                    # Then: the final answer
                    await real_bus.publish_outbound(
                        OutboundMessage(
                            channel=inbound.channel,
                            chat_id=inbound.chat_id,
                            content="The answer is 42",
                        )
                    )
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass

    mock_loop = MagicMock()
    mock_loop.run = _fake_agent_run
    mock_loop.stop = lambda: agent_stopped2.set()
    mock_loop.close_mcp = AsyncMock()

    printed_responses: list[str] = []
    user_inputs = iter(["What is 6 * 7?", "exit"])

    async def _mock_read_input() -> str:
        try:
            return next(user_inputs)
        except StopIteration:
            raise EOFError

    captured_coros2: list = []

    def _capture_asyncio_run2(coro):  # type: ignore[override]
        captured_coros2.append(coro)

    import nanobot.cli.commands as cmd_mod

    printed_hints: list[str] = []
    original_print = cmd_mod.console.print

    def _capture_print(s, *a, **kw):
        if isinstance(s, str) and "[dim]↳" in s:
            printed_hints.append(s)
        return original_print(s, *a, **kw)

    cmd_mod.console.print = _capture_print  # type: ignore[method-assign]
    try:
        with (
            patch("nanobot.bus.queue.MessageBus", return_value=real_bus),
            patch("nanobot.agent.loop.AgentLoop", return_value=mock_loop),
            patch("nanobot.config.loader.load_config", return_value=Config()),
            patch("nanobot.cli.commands._make_provider", return_value=MagicMock()),
            patch("nanobot.cron.service.CronService", return_value=MagicMock()),
            patch("nanobot.config.loader.get_data_dir", return_value=tmp_path),
            patch(
                "nanobot.cli.commands._read_interactive_input_async",
                side_effect=_mock_read_input,
            ),
            patch("nanobot.cli.commands._init_prompt_session"),
            patch("nanobot.cli.commands._flush_pending_tty_input"),
            patch("nanobot.cli.commands._restore_terminal"),
            patch(
                "nanobot.cli.commands._print_agent_response",
                side_effect=lambda r, **kw: printed_responses.append(r),
            ),
            patch("asyncio.run", side_effect=_capture_asyncio_run2),
        ):
            from nanobot.cli.commands import agent

            agent(  # type: ignore[arg-type]
                message=None, session_id="cli:test", markdown=True, logs=False
            )

            # agent() called asyncio.run(run_interactive()) — await it while patches are active
            assert len(captured_coros2) == 1, "Expected asyncio.run called once for run_interactive"
            await captured_coros2[0]
    finally:
        cmd_mod.console.print = original_print

    # Progress hint must be displayed via console.print with Rich markup
    assert len(printed_hints) == 1, f"Expected 1 progress hint, got {printed_hints}"
    assert "Calling tool: shell" in printed_hints[0]

    # Final response must be routed to _print_agent_response
    assert len(printed_responses) == 1, f"Expected 1 response, got {printed_responses}"
    assert printed_responses[0] == "The answer is 42"
