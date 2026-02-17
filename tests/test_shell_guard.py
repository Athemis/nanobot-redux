import asyncio
import shlex

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


class _FakeProcess:
    def __init__(self, stdout: bytes = b"ok", stderr: bytes = b"", returncode: int = 0) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def kill(self) -> None:
        return None


@pytest.mark.asyncio
async def test_execute_uses_raw_command_when_wrapper_is_blank(monkeypatch) -> None:
    captured: dict[str, str] = {}

    async def _fake_create_subprocess_shell(command: str, **_: object) -> _FakeProcess:
        captured["command"] = command
        return _FakeProcess(stdout=b"ok")

    monkeypatch.setattr(asyncio, "create_subprocess_shell", _fake_create_subprocess_shell)

    tool = ExecTool(command_wrapper="   ")
    result = await tool.execute("echo hello")

    assert result == "ok"
    assert captured["command"] == "echo hello"


@pytest.mark.asyncio
async def test_execute_wraps_full_command_as_single_posix_payload(monkeypatch) -> None:
    captured: dict[str, str] = {}

    async def _fake_create_subprocess_shell(command: str, **_: object) -> _FakeProcess:
        captured["command"] = command
        return _FakeProcess(stdout=b"ok")

    monkeypatch.setattr(asyncio, "create_subprocess_shell", _fake_create_subprocess_shell)

    wrapper = "bwrap --ro-bind / / --dev /dev --proc /proc --"
    command = "echo one; echo two && echo three | cat"
    tool = ExecTool(command_wrapper=wrapper)
    result = await tool.execute(command)

    assert result == "ok"
    assert captured["command"] == f"{wrapper} sh -lc {shlex.quote(command)}"


@pytest.mark.asyncio
async def test_execute_blocks_raw_command_before_wrapper_invocation(monkeypatch) -> None:
    called = False

    async def _fake_create_subprocess_shell(command: str, **_: object) -> _FakeProcess:
        nonlocal called
        called = True
        return _FakeProcess(stdout=b"ok")

    monkeypatch.setattr(asyncio, "create_subprocess_shell", _fake_create_subprocess_shell)

    tool = ExecTool(command_wrapper="bwrap --ro-bind / / --")
    result = await tool.execute("mkfs.ext4 /dev/sda")

    assert result == "Error: Command blocked by safety guard (dangerous pattern detected)"
    assert called is False
