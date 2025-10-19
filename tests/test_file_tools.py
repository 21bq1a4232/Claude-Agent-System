"""Tests for FileTools."""

import pytest
import tempfile
from pathlib import Path
from mcp_server.tools.file_tools import FileTools
from mcp_server.permissions import PermissionManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def permission_manager():
    """Create a mock permission manager."""
    # Create a temporary permissions config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
mode: permissive
safe_directories:
  - /tmp
blocked_directories:
  - /etc
require_approval: []
""")
        config_path = f.name

    pm = PermissionManager(config_path)
    yield pm

    # Cleanup
    Path(config_path).unlink()


@pytest.fixture
def file_tools(permission_manager):
    """Create a FileTools instance."""
    config = {
        "tools": {
            "read": {"max_file_size_mb": 10},
            "write": {"backup": {"enabled": True, "suffix": ".backup"}},
        }
    }
    return FileTools(permission_manager, config)


@pytest.mark.asyncio
async def test_write_and_read_file(file_tools, temp_dir):
    """Test writing and reading a file."""
    test_file = temp_dir / "test.txt"
    content = "Hello, World!\nThis is a test file."

    # Write file
    write_result = await file_tools.write_file(str(test_file), content)

    assert write_result["success"] is True
    assert write_result["lines_written"] == 2
    assert write_result["operation"] == "create"

    # Read file
    read_result = await file_tools.read_file(str(test_file))

    assert read_result["success"] is True
    assert read_result["total_lines"] == 2
    assert "Hello, World!" in read_result["content"]


@pytest.mark.asyncio
async def test_read_file_with_offset_limit(file_tools, temp_dir):
    """Test reading file with offset and limit."""
    test_file = temp_dir / "test.txt"
    content = "\n".join([f"Line {i}" for i in range(1, 11)])

    await file_tools.write_file(str(test_file), content)

    # Read with offset and limit
    read_result = await file_tools.read_file(str(test_file), offset=3, limit=5)

    assert read_result["success"] is True
    assert read_result["lines_returned"] == 5
    assert read_result["start_line"] == 3


@pytest.mark.asyncio
async def test_edit_file(file_tools, temp_dir):
    """Test editing a file."""
    test_file = temp_dir / "test.txt"
    original_content = "Hello, World!\nThis is a test."

    await file_tools.write_file(str(test_file), original_content)

    # Edit file
    edit_result = await file_tools.edit_file(
        str(test_file), "World", "Python", replace_all=False
    )

    assert edit_result["success"] is True
    assert edit_result["replacements_made"] == 1

    # Verify edit
    read_result = await file_tools.read_file(str(test_file))
    assert "Hello, Python!" in read_result["content"]


@pytest.mark.asyncio
async def test_edit_file_replace_all(file_tools, temp_dir):
    """Test editing a file with replace_all."""
    test_file = temp_dir / "test.txt"
    content = "foo bar foo baz foo"

    await file_tools.write_file(str(test_file), content)

    # Edit with replace_all
    edit_result = await file_tools.edit_file(
        str(test_file), "foo", "qux", replace_all=True
    )

    assert edit_result["success"] is True
    assert edit_result["replacements_made"] == 3


@pytest.mark.asyncio
async def test_edit_file_not_found(file_tools, temp_dir):
    """Test editing a file with string not found."""
    test_file = temp_dir / "test.txt"
    content = "Hello, World!"

    await file_tools.write_file(str(test_file), content)

    # Try to edit with non-existent string
    edit_result = await file_tools.edit_file(
        str(test_file), "NonExistent", "Replacement"
    )

    # Check that the operation failed
    # Error response structure: {"error": True, "message": "...", "error_type": "..."}
    assert edit_result.get("error") is True
    assert "message" in edit_result
    error_msg = edit_result["message"]
    assert "not found" in error_msg.lower() or "NonExistent" in error_msg


@pytest.mark.asyncio
async def test_list_directory(file_tools, temp_dir):
    """Test listing directory contents."""
    # Create test files and directories
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.py").write_text("content2")
    (temp_dir / "subdir").mkdir()

    # List directory
    list_result = await file_tools.list_directory(str(temp_dir))

    assert list_result["success"] is True
    assert list_result["total_items"] == 3
    assert len(list_result["files"]) == 2
    assert len(list_result["directories"]) == 1


@pytest.mark.asyncio
async def test_list_directory_with_pattern(file_tools, temp_dir):
    """Test listing directory with pattern."""
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.py").write_text("content2")
    (temp_dir / "file3.txt").write_text("content3")

    # List with pattern
    list_result = await file_tools.list_directory(str(temp_dir), pattern="*.txt")

    assert list_result["success"] is True
    assert len(list_result["files"]) == 2


@pytest.mark.asyncio
async def test_delete_file(file_tools, temp_dir):
    """Test deleting a file."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("content")

    # Delete file
    delete_result = await file_tools.delete_file(str(test_file))

    assert delete_result["success"] is True
    assert not test_file.exists()


@pytest.mark.asyncio
async def test_file_backup_on_write(file_tools, temp_dir):
    """Test that backup is created on file overwrite."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("original content")

    # Overwrite file
    write_result = await file_tools.write_file(str(test_file), "new content")

    assert write_result["success"] is True
    assert write_result["backup_created"] is True
    assert write_result["operation"] == "overwrite"

    # Check backup exists
    backup_path = Path(write_result["backup_path"])
    assert backup_path.exists()
    assert backup_path.read_text() == "original content"
