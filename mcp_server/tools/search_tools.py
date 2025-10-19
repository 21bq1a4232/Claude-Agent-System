"""Search operation tools (Grep, Glob)."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp_server.permissions import PermissionManager, InputValidator
from mcp_server.utils import get_logger, ToolError, create_error_response


logger = get_logger(__name__)


class SearchTools:
    """Search operation tools."""

    def __init__(self, permission_manager: PermissionManager, config: Dict[str, Any]):
        """
        Initialize search tools.

        Args:
            permission_manager: Permission manager instance
            config: Tool configuration
        """
        self.permission_manager = permission_manager
        self.config = config.get("tools", {})

    async def grep(
        self,
        pattern: str,
        path: str = ".",
        regex: bool = False,
        case_insensitive: bool = False,
        context_before: int = 0,
        context_after: int = 0,
        max_results: Optional[int] = None,
        file_pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for patterns in files (like ripgrep/grep).

        Args:
            pattern: Pattern to search for
            path: File or directory to search in
            regex: Whether pattern is a regex
            case_insensitive: Case insensitive search
            context_before: Lines of context before match
            context_after: Lines of context after match
            max_results: Maximum number of results
            file_pattern: Glob pattern to filter files

        Returns:
            Dictionary with search results
        """
        try:
            # Validate inputs
            search_path = InputValidator.validate_file_path(path, must_exist=True)
            InputValidator.validate_pattern(pattern, "regex" if regex else "glob")

            # Get config
            grep_config = self.config.get("grep", {})
            max_results = max_results or grep_config.get("max_results", 1000)

            # Compile pattern
            flags = re.IGNORECASE if case_insensitive else 0
            try:
                if regex:
                    compiled_pattern = re.compile(pattern, flags)
                else:
                    # Escape for literal search
                    escaped_pattern = re.escape(pattern)
                    compiled_pattern = re.compile(escaped_pattern, flags)
            except re.error as e:
                raise ToolError(f"Invalid pattern: {e}")

            # Collect files to search
            files_to_search = []
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                # Directory search
                if file_pattern:
                    files_to_search = list(search_path.rglob(file_pattern))
                else:
                    files_to_search = [f for f in search_path.rglob("*") if f.is_file()]

            # Exclude patterns from config
            exclude_patterns = grep_config.get("exclude_patterns", [])
            files_to_search = [
                f
                for f in files_to_search
                if not any(f.match(excl) for excl in exclude_patterns)
            ]

            # Search in files
            results = []
            total_matches = 0

            for file_path in files_to_search:
                try:
                    # Check permission for each file
                    self.permission_manager.check_file_access(str(file_path), operation="read")

                    # Read and search
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, start=1):
                        if compiled_pattern.search(line):
                            total_matches += 1

                            # Extract context
                            context_start = max(0, line_num - 1 - context_before)
                            context_end = min(len(lines), line_num + context_after)

                            match_result = {
                                "file": str(file_path),
                                "line_number": line_num,
                                "line": line.rstrip(),
                            }

                            if context_before > 0 or context_after > 0:
                                context_lines = []
                                for i in range(context_start, context_end):
                                    context_lines.append({
                                        "line_number": i + 1,
                                        "line": lines[i].rstrip(),
                                        "is_match": i + 1 == line_num,
                                    })
                                match_result["context"] = context_lines

                            results.append(match_result)

                            if len(results) >= max_results:
                                break

                except Exception as e:
                    logger.warning(f"Error searching {file_path}: {e}")
                    continue

                if len(results) >= max_results:
                    break

            return {
                "success": True,
                "pattern": pattern,
                "search_path": str(search_path),
                "total_matches": total_matches,
                "results_returned": len(results),
                "truncated": total_matches > len(results),
                "matches": results,
            }

        except Exception as e:
            logger.error(f"Error in grep: {e}")
            return create_error_response(e)

    async def glob(
        self,
        pattern: str,
        path: str = ".",
        max_results: Optional[int] = None,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """
        Find files matching glob patterns.

        Args:
            pattern: Glob pattern (e.g., "**/*.py")
            path: Base directory to search from
            max_results: Maximum number of results
            include_hidden: Include hidden files/directories

        Returns:
            Dictionary with matching files
        """
        try:
            # Validate inputs
            search_path = InputValidator.validate_file_path(path, must_exist=True)
            InputValidator.validate_pattern(pattern, "glob")

            if not search_path.is_dir():
                raise ToolError(f"Path must be a directory: {search_path}")

            # Check permission
            self.permission_manager.check_file_access(str(search_path), operation="read")

            # Get config
            glob_config = self.config.get("glob", {})
            max_results = max_results or glob_config.get("max_results", 1000)
            exclude_patterns = glob_config.get("exclude_patterns", [])

            # Search for files
            matches = []
            for file_path in search_path.rglob(pattern):
                # Skip hidden files if not included
                if not include_hidden and any(part.startswith(".") for part in file_path.parts):
                    continue

                # Skip excluded patterns
                if any(file_path.match(excl) for excl in exclude_patterns):
                    continue

                # Get file info
                try:
                    stat = file_path.stat()
                    matches.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "is_file": file_path.is_file(),
                        "is_dir": file_path.is_dir(),
                        "size": stat.st_size if file_path.is_file() else 0,
                        "modified": stat.st_mtime,
                    })

                    if len(matches) >= max_results:
                        break

                except Exception as e:
                    logger.warning(f"Error getting info for {file_path}: {e}")
                    continue

            # Sort by modification time (most recent first)
            matches.sort(key=lambda x: x["modified"], reverse=True)

            return {
                "success": True,
                "pattern": pattern,
                "search_path": str(search_path),
                "total_matches": len(matches),
                "truncated": len(matches) >= max_results,
                "matches": matches,
            }

        except Exception as e:
            logger.error(f"Error in glob: {e}")
            return create_error_response(e)

    async def find(
        self,
        name: Optional[str] = None,
        path: str = ".",
        file_type: Optional[str] = None,
        max_depth: Optional[int] = None,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Find files by name and type (Unix find-like).

        Args:
            name: File name pattern
            path: Base directory to search from
            file_type: Type filter ('f' for file, 'd' for directory)
            max_depth: Maximum directory depth
            max_results: Maximum number of results

        Returns:
            Dictionary with matching files
        """
        try:
            # Validate inputs
            search_path = InputValidator.validate_file_path(path, must_exist=True)

            if not search_path.is_dir():
                raise ToolError(f"Path must be a directory: {search_path}")

            # Check permission
            self.permission_manager.check_file_access(str(search_path), operation="read")

            # Get config
            max_results = max_results or 1000

            # Build pattern
            pattern = name if name else "*"

            # Search
            matches = []

            def search_recursive(current_path: Path, depth: int = 0) -> None:
                if max_depth and depth > max_depth:
                    return

                if len(matches) >= max_results:
                    return

                try:
                    for item in current_path.iterdir():
                        # Check type filter
                        if file_type == "f" and not item.is_file():
                            continue
                        if file_type == "d" and not item.is_dir():
                            continue

                        # Check name pattern
                        if pattern != "*" and not item.match(pattern):
                            if item.is_dir():
                                search_recursive(item, depth + 1)
                            continue

                        # Add match
                        stat = item.stat()
                        matches.append({
                            "path": str(item),
                            "name": item.name,
                            "is_file": item.is_file(),
                            "is_dir": item.is_dir(),
                            "size": stat.st_size if item.is_file() else 0,
                            "modified": stat.st_mtime,
                            "depth": depth,
                        })

                        if len(matches) >= max_results:
                            return

                        # Recurse into directories
                        if item.is_dir():
                            search_recursive(item, depth + 1)

                except PermissionError:
                    logger.warning(f"Permission denied: {current_path}")
                except Exception as e:
                    logger.warning(f"Error searching {current_path}: {e}")

            search_recursive(search_path)

            return {
                "success": True,
                "name_pattern": pattern,
                "search_path": str(search_path),
                "file_type": file_type,
                "max_depth": max_depth,
                "total_matches": len(matches),
                "truncated": len(matches) >= max_results,
                "matches": matches,
            }

        except Exception as e:
            logger.error(f"Error in find: {e}")
            return create_error_response(e)
