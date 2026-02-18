import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.tools.shell import ExecTool

BLOCKED_COMMANDS = [
    "mkfs.ext4 /dev/sda",
    "sudo mkfs.ext4 /dev/sda",
    r"cmd /c C:\\Windows\\System32\\format.com c:",
    r"C:\\Windows\\System32\\format.com c:",
    r"cmd.exe /c shutdown /r /t 0",
    r"cmd /c C:\\Windows\\System32\\shutdown.exe /r /t 0",
    r"C:\\Windows\\System32\\shutdown.exe /s /t 0",
    r"\\server\share\mkfs.exe /dev/sda",
    r"\\server\share\shutdown.exe /r /t 0",
    "(mkfs.ext4 /dev/sda)",
    "$(mkfs.ext4 /dev/sda)",
    "bash -lc \"mkfs.ext4 /dev/sda\"",
    "shutdown now",
    "sudo shutdown -h now",
    "$(reboot)",
    "bash -lc \"shutdown now\"",
    "env PATH=/tmp shutdown now",
    "sudo env FOO=1 mkfs.ext4 /dev/sda",
]

ALLOWED_COMMANDS = [
    "curl -s \"wttr.in/London?format=3\"",
    "echo mkfs.ext4 /dev/sda",
    "bash -lc \"echo mkfs.ext4 /dev/sda\"",
    "echo shutdown now",
    "bash -lc \"echo shutdown now\"",
    "env PATH=/tmp echo shutdown now",
    r"cmd /c echo shutdown now",
    r"cmd /c echo C:\\Windows\\System32\\format.com c:",
    r"echo C:\\Windows\\System32\\shutdown.exe /s /t 0",
    r"echo \\server\share\mkfs.exe /dev/sda",
    "FOO=shutdown",
]


@pytest.mark.parametrize("command", BLOCKED_COMMANDS)
def test_guard_blocks_destructive_commands_in_prefixed_and_nested_contexts(command: str) -> None:
    tool = ExecTool()

    result = tool._guard_command(command, cwd=".")

    assert result == "Error: Command blocked by safety guard (dangerous pattern detected)"


@pytest.mark.parametrize("command", ALLOWED_COMMANDS)
def test_guard_allows_non_executing_text_mentions(command: str) -> None:
    tool = ExecTool()

    result = tool._guard_command(command, cwd=".")

    assert result is None


# ---------------------------------------------------------------------------
# ExecTool.execute() tests
# ---------------------------------------------------------------------------


def _make_proc(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    return proc


@pytest.mark.asyncio
async def test_execute_returns_stdout_on_success(tmp_path: Path) -> None:
    tool = ExecTool(working_dir=str(tmp_path))
    proc = _make_proc(stdout=b"hello world\n")

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=proc)):
        result = await tool.execute("echo hello world")

    assert "hello world" in result


@pytest.mark.asyncio
async def test_execute_captures_stderr(tmp_path: Path) -> None:
    tool = ExecTool(working_dir=str(tmp_path))
    proc = _make_proc(stderr=b"something went wrong\n", returncode=1)

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=proc)):
        result = await tool.execute("false")

    assert "STDERR:" in result
    assert "something went wrong" in result
    assert "Exit code: 1" in result


@pytest.mark.asyncio
async def test_execute_includes_exit_code_on_failure(tmp_path: Path) -> None:
    tool = ExecTool(working_dir=str(tmp_path))
    proc = _make_proc(returncode=42)

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=proc)):
        result = await tool.execute("exit 42")

    assert "Exit code: 42" in result


@pytest.mark.asyncio
async def test_execute_returns_no_output_sentinel(tmp_path: Path) -> None:
    tool = ExecTool(working_dir=str(tmp_path))
    proc = _make_proc(stdout=b"", stderr=b"", returncode=0)

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=proc)):
        result = await tool.execute("true")

    assert result == "(no output)"


@pytest.mark.asyncio
async def test_execute_blocked_by_guard_does_not_spawn_process(tmp_path: Path) -> None:
    tool = ExecTool(working_dir=str(tmp_path))

    with patch("asyncio.create_subprocess_shell", new=AsyncMock()) as mock_spawn:
        result = await tool.execute("rm -rf /")

    mock_spawn.assert_not_called()
    assert "blocked by safety guard" in result


@pytest.mark.asyncio
async def test_execute_timeout_kills_process_and_returns_error(tmp_path: Path) -> None:
    tool = ExecTool(timeout=1, working_dir=str(tmp_path))

    proc = MagicMock()
    proc.returncode = None
    proc.kill = MagicMock()

    async def slow_communicate():
        await asyncio.sleep(10)
        return b"", b""

    proc.communicate = slow_communicate

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=proc)):
        result = await tool.execute("sleep 10")

    proc.kill.assert_called_once()
    assert "timed out" in result
    assert "1 seconds" in result


@pytest.mark.asyncio
async def test_execute_truncates_very_long_output(tmp_path: Path) -> None:
    tool = ExecTool(working_dir=str(tmp_path))
    long_output = b"x" * 20000
    proc = _make_proc(stdout=long_output)

    with patch("asyncio.create_subprocess_shell", new=AsyncMock(return_value=proc)):
        result = await tool.execute("cat big_file")

    assert "truncated" in result
    assert len(result) < 20000


@pytest.mark.asyncio
async def test_execute_uses_provided_working_dir_override(tmp_path: Path) -> None:
    tool = ExecTool()
    proc = _make_proc(stdout=b"ok\n")

    captured_kwargs: dict = {}

    async def fake_subprocess(cmd, **kwargs):
        captured_kwargs.update(kwargs)
        return proc

    with patch("asyncio.create_subprocess_shell", new=fake_subprocess):
        await tool.execute("pwd", working_dir=str(tmp_path))

    assert captured_kwargs.get("cwd") == str(tmp_path)


@pytest.mark.asyncio
async def test_execute_exception_returns_error_string(tmp_path: Path) -> None:
    tool = ExecTool(working_dir=str(tmp_path))

    async def boom(*_a, **_kw):
        raise OSError("no such file or directory")

    with patch("asyncio.create_subprocess_shell", new=boom):
        result = await tool.execute("nonexistent_cmd")

    assert result.startswith("Error executing command:")
    assert "no such file or directory" in result



# ---------------------------------------------------------------------------
# _guard_command workspace-restriction tests
# ---------------------------------------------------------------------------


def test_guard_workspace_restriction_blocks_path_traversal(tmp_path: Path) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    result = tool._guard_command("cat ../secret.txt", cwd=str(tmp_path))
    assert result is not None
    assert "path traversal" in result


def test_guard_workspace_restriction_blocks_absolute_path_outside_cwd(tmp_path: Path) -> None:
    cwd = tmp_path / "workspace"
    cwd.mkdir()
    tool = ExecTool(restrict_to_workspace=True)
    result = tool._guard_command("cat /etc/passwd", cwd=str(cwd))
    assert result is not None
    assert "outside working dir" in result


def test_guard_workspace_restriction_allows_path_inside_cwd(tmp_path: Path) -> None:
    cwd = tmp_path / "workspace"
    cwd.mkdir()
    inside = cwd / "notes.txt"
    inside.write_text("hi")
    tool = ExecTool(restrict_to_workspace=True)
    result = tool._guard_command(f"cat {inside}", cwd=str(cwd))
    assert result is None


def test_guard_workspace_restriction_allows_simple_commands(tmp_path: Path) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    result = tool._guard_command("ls -la", cwd=str(tmp_path))
    assert result is None


def test_guard_allow_patterns_blocks_command_not_in_allowlist() -> None:
    tool = ExecTool(allow_patterns=[r"^echo"])
    result = tool._guard_command("ls -la", cwd=".")
    assert result == "Error: Command blocked by safety guard (not in allowlist)"


def test_guard_allow_patterns_permits_matching_command() -> None:
    tool = ExecTool(allow_patterns=[r"^echo"])
    result = tool._guard_command("echo hello", cwd=".")
    assert result is None
