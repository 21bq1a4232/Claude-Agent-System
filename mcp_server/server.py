"""Main MCP server implementation."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from fastmcp import FastMCP

from mcp_server.tools import FileTools, SearchTools, ShellTools, WebTools
from mcp_server.permissions import PermissionManager
from mcp_server.utils import setup_logger, get_logger


class MCPServer:
    """MCP server with Claude Code-like tools."""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize MCP server.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.config = self._load_configs()

        # Setup logging
        log_config = self.config.get("tools_config", {}).get("logging", {})
        log_file = log_config.get("file", {})
        if log_file.get("enabled", True):
            log_path = log_file.get("path", "logs/mcp_server.log")
            self.logger = setup_logger(
                "mcp_server",
                level=log_config.get("level", "INFO"),
                log_file=log_path,
                max_size_mb=log_file.get("max_size_mb", 100),
                backup_count=log_file.get("backup_count", 5),
            )
        else:
            self.logger = setup_logger("mcp_server", level=log_config.get("level", "INFO"))

        self.logger.info("Initializing MCP Server...")

        # Initialize permission manager
        permissions_config_path = self.config_dir / "permissions_config.yaml"
        self.permission_manager = PermissionManager(str(permissions_config_path))

        # Initialize tools
        tools_config = self.config.get("tools_config", {})
        self.file_tools = FileTools(self.permission_manager, tools_config)
        self.search_tools = SearchTools(self.permission_manager, tools_config)
        self.shell_tools = ShellTools(self.permission_manager, tools_config)
        self.web_tools = WebTools(self.permission_manager, tools_config)

        # Create FastMCP instance
        self.mcp = FastMCP("claude-agent-mcp-server")
        self._register_tools()

        self.logger.info("MCP Server initialized successfully")

    def _load_configs(self) -> Dict[str, Any]:
        """Load all configuration files."""
        configs = {}

        config_files = {
            "agent_config": "agent_config.yaml",
            "tools_config": "tools_config.yaml",
            "permissions_config": "permissions_config.yaml",
        }

        for key, filename in config_files.items():
            config_path = self.config_dir / filename
            try:
                with open(config_path, "r") as f:
                    configs[key] = yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Failed to load {filename}: {e}")
                configs[key] = {}

        return configs

    def _register_tools(self) -> None:
        """Register all MCP tools."""
        self.logger.info("Registering MCP tools...")

        # File tools
        @self.mcp.tool()
        async def read_file(file_path: str, offset: Optional[int] = None, limit: Optional[int] = None):
            """
            Read a file from the filesystem.

            Args:
                file_path: Path to the file to read
                offset: Line number to start reading from (1-indexed)
                limit: Maximum number of lines to read
            """
            return await self.file_tools.read_file(file_path, offset, limit)

        @self.mcp.tool()
        async def write_file(file_path: str, content: str, create_backup: Optional[bool] = None):
            """
            Write content to a file.

            Args:
                file_path: Path to the file to write
                content: Content to write to the file
                create_backup: Whether to create a backup if file exists
            """
            return await self.file_tools.write_file(file_path, content, create_backup)

        @self.mcp.tool()
        async def edit_file(
            file_path: str,
            old_string: str,
            new_string: str,
            replace_all: bool = False,
        ):
            """
            Edit a file by replacing text.

            Args:
                file_path: Path to the file to edit
                old_string: Text to find and replace
                new_string: Text to replace with
                replace_all: Whether to replace all occurrences (default: False)
            """
            return await self.file_tools.edit_file(file_path, old_string, new_string, replace_all)

        @self.mcp.tool()
        async def list_directory(directory: str = ".", pattern: Optional[str] = None):
            """
            List contents of a directory.

            Args:
                directory: Directory path (default: current directory)
                pattern: Optional glob pattern to filter results
            """
            return await self.file_tools.list_directory(directory, pattern)

        # Search tools
        @self.mcp.tool()
        async def grep(
            pattern: str,
            path: str = ".",
            regex: bool = False,
            case_insensitive: bool = False,
            context_before: int = 0,
            context_after: int = 0,
            max_results: Optional[int] = None,
            file_pattern: Optional[str] = None,
        ):
            """
            Search for patterns in files (like ripgrep/grep).

            Args:
                pattern: Pattern to search for
                path: File or directory to search in (default: current directory)
                regex: Whether pattern is a regex (default: False)
                case_insensitive: Case insensitive search (default: False)
                context_before: Lines of context before match (default: 0)
                context_after: Lines of context after match (default: 0)
                max_results: Maximum number of results to return
                file_pattern: Glob pattern to filter files
            """
            return await self.search_tools.grep(
                pattern,
                path,
                regex,
                case_insensitive,
                context_before,
                context_after,
                max_results,
                file_pattern,
            )

        @self.mcp.tool()
        async def glob(pattern: str, path: str = ".", max_results: Optional[int] = None):
            """
            Find files matching glob patterns.

            Args:
                pattern: Glob pattern (e.g., "**/*.py")
                path: Base directory to search from (default: current directory)
                max_results: Maximum number of results to return
            """
            return await self.search_tools.glob(pattern, path, max_results)

        @self.mcp.tool()
        async def find(
            name: Optional[str] = None,
            path: str = ".",
            file_type: Optional[str] = None,
            max_depth: Optional[int] = None,
        ):
            """
            Find files by name and type (Unix find-like).

            Args:
                name: File name pattern
                path: Base directory to search from (default: current directory)
                file_type: Type filter ('f' for file, 'd' for directory)
                max_depth: Maximum directory depth to search
            """
            return await self.search_tools.find(name, path, file_type, max_depth)

        # Shell tools
        @self.mcp.tool()
        async def bash(
            command: str,
            timeout: Optional[int] = None,
            cwd: Optional[str] = None,
            background: bool = False,
        ):
            """
            Execute a bash command.

            Args:
                command: Command to execute
                timeout: Timeout in seconds
                cwd: Working directory
                background: Run in background (default: False)
            """
            return await self.shell_tools.bash(command, timeout, cwd, None, background)

        @self.mcp.tool()
        async def get_job_status(job_id: str):
            """
            Get status of a background job.

            Args:
                job_id: Job ID from background command execution
            """
            return await self.shell_tools.get_job_status(job_id)

        @self.mcp.tool()
        async def kill_job(job_id: str):
            """
            Kill a background job.

            Args:
                job_id: Job ID to kill
            """
            return await self.shell_tools.kill_job(job_id)

        # Web tools
        @self.mcp.tool()
        async def web_fetch(url: str, timeout: Optional[int] = None):
            """
            Fetch content from a URL.

            Args:
                url: URL to fetch
                timeout: Request timeout in seconds
            """
            return await self.web_tools.web_fetch(url, "GET", None, timeout)

        @self.mcp.tool()
        async def web_search(query: str, max_results: int = 10):
            """
            Search the web.

            Args:
                query: Search query
                max_results: Maximum number of results (default: 10)
            """
            return await self.web_tools.web_search(query, max_results)

        self.logger.info(f"Registered {len(self.mcp._tool_manager._tools)} MCP tools")

    async def run_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the MCP server using FastMCP's built-in SSE server."""
        self.logger.info(f"Starting FastMCP SSE server on {host}:{port}")

        # FastMCP handles the server internally
        await self.mcp.run_sse_async(host=host, port=port)


def create_server(config_dir: str = "config") -> MCPServer:
    """
    Create and return MCP server instance.

    Args:
        config_dir: Directory containing configuration files

    Returns:
        MCPServer instance
    """
    return MCPServer(config_dir)


# For direct execution
if __name__ == "__main__":
    import asyncio

    async def main():
        print("Starting MCP Server on http://localhost:8000")
        print("MCP SSE endpoint: http://localhost:8000/sse")
        print()
        server = create_server()
        await server.run_server(host="0.0.0.0", port=8000)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")
        import sys
        sys.exit(0)
