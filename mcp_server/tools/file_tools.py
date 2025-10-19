"""File operation tools (Read, Write, Edit)."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
import aiofiles
from mcp_server.permissions import PermissionManager, InputValidator
from mcp_server.utils import (
    get_logger,
    ToolError,
    FileNotFoundError as FileNotFoundToolError,
    create_error_response,
)


logger = get_logger(__name__)


class FileTools:
    """File operation tools."""

    def __init__(self, permission_manager: PermissionManager, config: Dict[str, Any]):
        """
        Initialize file tools.

        Args:
            permission_manager: Permission manager instance
            config: Tool configuration
        """
        self.permission_manager = permission_manager
        self.config = config.get("tools", {})

    async def read_file(
        self,
        file_path: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Read a file from the filesystem.

        Args:
            file_path: Path to the file
            offset: Line number to start reading from (1-indexed)
            limit: Maximum number of lines to read

        Returns:
            Dictionary with file contents and metadata
        """
        try:
            # Validate input
            path = InputValidator.validate_file_path(file_path, must_exist=True)

            # Check permissions
            self.permission_manager.check_file_access(str(path), operation="read")

            # Check file size
            max_size_mb = self.config.get("read", {}).get("max_file_size_mb", 10)
            file_size = path.stat().st_size
            if file_size > max_size_mb * 1024 * 1024:
                raise ToolError(
                    f"File too large: {file_size / (1024 * 1024):.2f}MB (max: {max_size_mb}MB)",
                    details={"file_size_mb": file_size / (1024 * 1024), "max_size_mb": max_size_mb},
                    suggestions=["Use offset and limit to read portions of the file"],
                )

            # Read file
            async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = await f.readlines()

            total_lines = len(lines)

            # Apply offset and limit
            if offset is not None:
                offset = max(1, offset)  # 1-indexed
                lines = lines[offset - 1 :]

            if limit is not None:
                limit = max(1, limit)
                lines = lines[:limit]

            # Format with line numbers
            start_line = offset if offset else 1
            formatted_lines = []
            for i, line in enumerate(lines, start=start_line):
                formatted_lines.append(f"{i:6d}\t{line.rstrip()}")

            content = "\n".join(formatted_lines)

            return {
                "success": True,
                "file_path": str(path),
                "total_lines": total_lines,
                "lines_returned": len(lines),
                "start_line": start_line,
                "content": content,
            }

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return create_error_response(e)

    async def write_file(
        self,
        file_path: str,
        content: str,
        create_backup: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Write content to a file.

        Args:
            file_path: Path to the file
            content: Content to write
            create_backup: Whether to create backup if file exists

        Returns:
            Dictionary with operation result
        """
        try:
            # Validate input
            path = InputValidator.validate_file_path(file_path)

            # Check if file exists
            file_exists = path.exists()

            # Check permissions
            self.permission_manager.check_file_access(
                str(path),
                operation="write",
            )

            # Backup if needed
            backup_config = self.config.get("write", {}).get("backup", {})
            should_backup = create_backup if create_backup is not None else backup_config.get("enabled", True)

            backup_path = None
            if file_exists and should_backup:
                backup_suffix = backup_config.get("suffix", ".backup")
                backup_path = Path(str(path) + backup_suffix)
                shutil.copy2(path, backup_path)
                logger.info(f"Created backup: {backup_path}")

            # Write file
            path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(content)

            lines_written = len(content.splitlines())

            return {
                "success": True,
                "file_path": str(path),
                "lines_written": lines_written,
                "bytes_written": len(content.encode("utf-8")),
                "backup_created": backup_path is not None,
                "backup_path": str(backup_path) if backup_path else None,
                "operation": "overwrite" if file_exists else "create",
            }

        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return create_error_response(e)

    async def edit_file(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> Dict[str, Any]:
        """
        Edit a file by replacing text.

        Args:
            file_path: Path to the file
            old_string: Text to find
            new_string: Text to replace with
            replace_all: Whether to replace all occurrences

        Returns:
            Dictionary with operation result
        """
        try:
            # Validate input
            path = InputValidator.validate_file_path(file_path, must_exist=True)

            # Check permissions
            self.permission_manager.check_file_access(str(path), operation="write")

            # Read current content
            async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as f:
                content = await f.read()

            # Count occurrences
            occurrences = content.count(old_string)

            if occurrences == 0:
                raise ToolError(
                    f"String not found in file: '{old_string}'",
                    details={"old_string": old_string},
                    suggestions=[
                        "Check if the string is correct",
                        "Use Grep to search for similar strings",
                        "Provide more context around the string",
                    ],
                )

            if occurrences > 1 and not replace_all:
                raise ToolError(
                    f"Found {occurrences} occurrences. Use replace_all=true to replace all.",
                    details={"occurrences": occurrences},
                    suggestions=["Set replace_all=true", "Provide more context to make the match unique"],
                )

            # Replace
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = occurrences
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Create backup
            backup_path = Path(str(path) + ".backup")
            shutil.copy2(path, backup_path)

            # Write new content
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(new_content)

            return {
                "success": True,
                "file_path": str(path),
                "replacements_made": replacements,
                "total_occurrences": occurrences,
                "replace_all": replace_all,
                "backup_path": str(backup_path),
            }

        except Exception as e:
            logger.error(f"Error editing file {file_path}: {e}")
            return create_error_response(e)

    async def delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        Delete a file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with operation result
        """
        try:
            # Validate input
            path = InputValidator.validate_file_path(file_path, must_exist=True)

            # Check permissions (always requires approval for delete)
            self.permission_manager.check_file_access(str(path), operation="delete")

            # Delete
            path.unlink()

            return {
                "success": True,
                "file_path": str(path),
                "operation": "deleted",
            }

        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return create_error_response(e)

    async def list_directory(
        self,
        directory: str = ".",
        pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List contents of a directory.

        Args:
            directory: Directory path
            pattern: Optional glob pattern

        Returns:
            Dictionary with directory contents
        """
        try:
            # Validate input
            dir_path = InputValidator.validate_file_path(directory, must_exist=True)

            if not dir_path.is_dir():
                raise ToolError(f"Not a directory: {dir_path}")

            # Check permissions
            self.permission_manager.check_file_access(str(dir_path), operation="read")

            # List files
            if pattern:
                items = list(dir_path.glob(pattern))
            else:
                items = list(dir_path.iterdir())

            # Sort and categorize
            files = []
            directories = []

            for item in sorted(items):
                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": item.stat().st_mtime,
                }

                if item.is_dir():
                    directories.append(item_info)
                else:
                    files.append(item_info)

            return {
                "success": True,
                "directory": str(dir_path),
                "total_items": len(files) + len(directories),
                "files": files,
                "directories": directories,
            }

        except Exception as e:
            logger.error(f"Error listing directory {directory}: {e}")
            return create_error_response(e)
