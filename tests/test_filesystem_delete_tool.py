from pathlib import Path

import pytest

from nanobot.agent.tools.filesystem import (
    DeleteFileTool,
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from nanobot.agent.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_delete_file_success(tmp_path: Path) -> None:
    file_path = tmp_path / "to_delete.txt"
    file_path.write_text("data", encoding="utf-8")

    tool = DeleteFileTool()
    result = await tool.execute(path=str(file_path))

    assert result == f"Successfully deleted {file_path}"
    assert not file_path.exists()


@pytest.mark.asyncio
async def test_delete_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"

    tool = DeleteFileTool()
    result = await tool.execute(path=str(missing))

    assert result == f"Error: File not found: {missing}"


@pytest.mark.asyncio
async def test_delete_file_rejects_directory(tmp_path: Path) -> None:
    dir_path = tmp_path / "folder"
    dir_path.mkdir()

    tool = DeleteFileTool()
    result = await tool.execute(path=str(dir_path))

    assert result == f"Error: Not a file: {dir_path}"


@pytest.mark.asyncio
async def test_delete_file_requires_path_parameter_via_schema(tmp_path: Path) -> None:
    file_path = tmp_path / "keep.txt"
    file_path.write_text("data", encoding="utf-8")

    registry = ToolRegistry()
    registry.register(DeleteFileTool())

    result = await registry.execute("delete_file", {})

    assert "Error: Invalid parameters for tool 'delete_file'" in result
    assert "missing required path" in result
    assert file_path.exists()


@pytest.mark.asyncio
async def test_delete_file_blocks_path_outside_allowed_dir(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("data", encoding="utf-8")

    tool = DeleteFileTool(allowed_dir=allowed_dir)
    result = await tool.execute(path=str(outside_file))

    assert result == f"Error: Path {outside_file} is outside allowed directory {allowed_dir}"
    assert outside_file.exists()


@pytest.mark.asyncio
async def test_delete_file_removes_symlink_not_target(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    target = tmp_path / "target.txt"
    target.write_text("data", encoding="utf-8")

    link = allowed_dir / "target_link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks are not supported in this environment")

    tool = DeleteFileTool(allowed_dir=allowed_dir)
    result = await tool.execute(path=str(link))

    assert result == f"Successfully deleted {link}"
    assert not link.exists()
    assert target.exists()


@pytest.mark.asyncio
async def test_delete_file_blocks_symlinked_parent_escape(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    outside_file = outside_dir / "outside.txt"
    outside_file.write_text("data", encoding="utf-8")

    escaped_parent = allowed_dir / "escape"
    try:
        escaped_parent.symlink_to(outside_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks are not supported in this environment")

    tool = DeleteFileTool(allowed_dir=allowed_dir)
    escaped_path = escaped_parent / "outside.txt"
    result = await tool.execute(path=str(escaped_path))

    assert result == f"Error: Path {escaped_path} is outside allowed directory {allowed_dir}"
    assert outside_file.exists()


@pytest.mark.asyncio
async def test_delete_file_allows_symlinked_allowed_dir(tmp_path: Path) -> None:
    real_workspace = tmp_path / "real_workspace"
    real_workspace.mkdir()

    allowed_link = tmp_path / "workspace_link"
    try:
        allowed_link.symlink_to(real_workspace, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks are not supported in this environment")

    file_via_link = allowed_link / "inside.txt"
    file_via_link.write_text("data", encoding="utf-8")

    tool = DeleteFileTool(allowed_dir=allowed_link)
    result = await tool.execute(path=str(file_via_link))

    assert result == f"Successfully deleted {file_via_link}"
    assert not file_via_link.exists()


# ---------------------------------------------------------------------------
# ReadFileTool additional coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_file_returns_error_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.txt"

    tool = ReadFileTool()
    result = await tool.execute(path=str(missing))

    assert result == f"Error: File not found: {missing}"


@pytest.mark.asyncio
async def test_read_file_returns_error_for_directory(tmp_path: Path) -> None:
    dir_path = tmp_path / "adir"
    dir_path.mkdir()

    tool = ReadFileTool()
    result = await tool.execute(path=str(dir_path))

    assert result == f"Error: Not a file: {dir_path}"


@pytest.mark.asyncio
async def test_read_file_permission_error_returns_error_string(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    tool = ReadFileTool(allowed_dir=workspace)
    result = await tool.execute(path=str(outside))

    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_read_file_no_restriction_reads_any_file(tmp_path: Path) -> None:
    f = tmp_path / "data.txt"
    f.write_text("content", encoding="utf-8")

    tool = ReadFileTool()
    result = await tool.execute(path=str(f))

    assert result == "content"



# ---------------------------------------------------------------------------
# WriteFileTool coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_file_creates_file_with_content(tmp_path: Path) -> None:
    dest = tmp_path / "new_file.txt"

    tool = WriteFileTool()
    result = await tool.execute(path=str(dest), content="hello write")

    assert "Successfully wrote" in result
    assert dest.read_text(encoding="utf-8") == "hello write"


@pytest.mark.asyncio
async def test_write_file_creates_parent_dirs(tmp_path: Path) -> None:
    dest = tmp_path / "sub" / "nested" / "file.txt"

    tool = WriteFileTool()
    result = await tool.execute(path=str(dest), content="nested")

    assert "Successfully wrote" in result
    assert dest.exists()


@pytest.mark.asyncio
async def test_write_file_blocks_path_outside_allowed_dir(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    outside = tmp_path / "outside.txt"

    tool = WriteFileTool(allowed_dir=allowed_dir)
    result = await tool.execute(path=str(outside), content="data")

    assert result.startswith("Error:")
    assert not outside.exists()


@pytest.mark.asyncio
async def test_write_file_overwrites_existing_file(tmp_path: Path) -> None:
    dest = tmp_path / "existing.txt"
    dest.write_text("old content", encoding="utf-8")

    tool = WriteFileTool()
    result = await tool.execute(path=str(dest), content="new content")

    assert "Successfully wrote" in result
    assert dest.read_text(encoding="utf-8") == "new content"



# ---------------------------------------------------------------------------
# EditFileTool coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_file_replaces_text(tmp_path: Path) -> None:
    f = tmp_path / "edit_me.txt"
    f.write_text("hello world", encoding="utf-8")

    tool = EditFileTool()
    result = await tool.execute(path=str(f), old_text="world", new_text="there")

    assert result == f"Successfully edited {f}"
    assert f.read_text(encoding="utf-8") == "hello there"


@pytest.mark.asyncio
async def test_edit_file_returns_error_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "no_file.txt"

    tool = EditFileTool()
    result = await tool.execute(path=str(missing), old_text="x", new_text="y")

    assert result == f"Error: File not found: {missing}"


@pytest.mark.asyncio
async def test_edit_file_returns_error_when_old_text_not_found(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("hello world", encoding="utf-8")

    tool = EditFileTool()
    result = await tool.execute(path=str(f), old_text="nonexistent", new_text="y")

    assert "old_text not found" in result


@pytest.mark.asyncio
async def test_edit_file_warns_on_multiple_occurrences(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("aaa", encoding="utf-8")

    tool = EditFileTool()
    result = await tool.execute(path=str(f), old_text="a", new_text="b")

    assert "appears" in result
    assert "3 times" in result


@pytest.mark.asyncio
async def test_edit_file_blocks_path_outside_allowed_dir(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("data", encoding="utf-8")

    tool = EditFileTool(allowed_dir=allowed_dir)
    result = await tool.execute(path=str(outside), old_text="data", new_text="x")

    assert result.startswith("Error:")



# ---------------------------------------------------------------------------
# ListDirTool coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_dir_returns_contents(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("x")
    (tmp_path / "subdir").mkdir()

    tool = ListDirTool()
    result = await tool.execute(path=str(tmp_path))

    assert "file.txt" in result
    assert "subdir" in result


@pytest.mark.asyncio
async def test_list_dir_returns_empty_message_for_empty_dir(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    tool = ListDirTool()
    result = await tool.execute(path=str(empty_dir))

    assert "empty" in result.lower()


@pytest.mark.asyncio
async def test_list_dir_returns_error_for_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "missing_dir"

    tool = ListDirTool()
    result = await tool.execute(path=str(missing))

    assert result == f"Error: Directory not found: {missing}"


@pytest.mark.asyncio
async def test_list_dir_returns_error_for_file_path(tmp_path: Path) -> None:
    f = tmp_path / "a_file.txt"
    f.write_text("data")

    tool = ListDirTool()
    result = await tool.execute(path=str(f))

    assert result == f"Error: Not a directory: {f}"


@pytest.mark.asyncio
async def test_list_dir_blocks_path_outside_allowed_dir(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    tool = ListDirTool(allowed_dir=allowed_dir)
    result = await tool.execute(path=str(outside_dir))

    assert result.startswith("Error:")



# ---------------------------------------------------------------------------
# DeleteFileTool broken symlink coverage (lines 290-291 in filesystem.py)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_file_removes_broken_symlink(tmp_path: Path) -> None:
    link = tmp_path / "broken_link.txt"
    target = tmp_path / "gone_target.txt"

    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks are not supported in this environment")

    # Target does not exist - link is broken
    assert not target.exists()
    assert link.is_symlink()
    assert not link.exists()

    tool = DeleteFileTool()
    result = await tool.execute(path=str(link))

    assert result == f"Successfully deleted {link}"
    assert not link.is_symlink()

