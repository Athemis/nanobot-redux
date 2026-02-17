from pathlib import Path

import pytest

from nanobot.agent.tools.filesystem import ReadFileTool


@pytest.mark.asyncio
async def test_read_file_allows_workspace_path(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("hello", encoding="utf-8")

    tool = ReadFileTool(allowed_dir=tmp_path)
    result = await tool.execute(path=str(f))

    assert result == "hello"


@pytest.mark.asyncio
async def test_read_file_blocks_path_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    tool = ReadFileTool(allowed_dir=workspace)
    result = await tool.execute(path=str(outside))

    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_read_file_extra_allowed_dirs_permits_builtin_skill(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    builtin = tmp_path / "builtin"
    builtin.mkdir()
    skill_file = builtin / "SKILL.md"
    skill_file.write_text("# skill", encoding="utf-8")

    tool = ReadFileTool(allowed_dir=workspace, extra_allowed_dirs=[builtin])
    result = await tool.execute(path=str(skill_file))

    assert result == "# skill"


@pytest.mark.asyncio
async def test_read_file_extra_allowed_dirs_still_blocks_other_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    builtin = tmp_path / "builtin"
    builtin.mkdir()
    other = tmp_path / "other" / "secret.txt"
    other.parent.mkdir()
    other.write_text("secret", encoding="utf-8")

    tool = ReadFileTool(allowed_dir=workspace, extra_allowed_dirs=[builtin])
    result = await tool.execute(path=str(other))

    assert result.startswith("Error:")
