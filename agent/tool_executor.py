"""Tool executor for MCP tools."""

import httpx
import json
from typing import Any, Dict, List, Optional
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


class ToolExecutor:
    """Executor for MCP tools via MCP SSE protocol."""

    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        """
        Initialize tool executor.

        Args:
            mcp_server_url: URL of the MCP server
        """
        self.mcp_server_url = mcp_server_url.rstrip("/")
        self.session: Optional[ClientSession] = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure MCP session is initialized."""
        if not self._initialized:
            try:
                # Create SSE client and session
                client_params = sse_client(url=f"{self.mcp_server_url}/sse")
                async with client_params as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self.session = session
                        self._initialized = True
            except Exception as e:
                raise Exception(f"Failed to initialize MCP client: {e}")

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            # Connect to MCP server and execute tool
            client_params = sse_client(url=f"{self.mcp_server_url}/sse")
            async with client_params as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Call the tool
                    result = await session.call_tool(tool_name, arguments)

                    # Return formatted result
                    return {
                        "tool": tool_name,
                        "arguments": arguments,
                        "result": result.content if hasattr(result, 'content') else result,
                        "success": True,
                    }

        except Exception as e:
            return {
                "tool": tool_name,
                "arguments": arguments,
                "error": f"Tool execution failed: {str(e)}",
                "success": False,
            }

    async def list_tools(self) -> List[str]:
        """
        List available tools from MCP server.

        Returns:
            List of tool names
        """
        try:
            # Connect to MCP server and list tools
            client_params = sse_client(url=f"{self.mcp_server_url}/sse")
            async with client_params as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # List tools
                    tools_result = await session.list_tools()
                    return [tool.name for tool in tools_result.tools]

        except Exception as e:
            # Fallback to known tools if server is not available
            print(f"Warning: Could not list tools from MCP server: {e}")
            return [
                "read_file",
                "write_file",
                "edit_file",
                "list_directory",
                "grep",
                "glob",
                "find",
                "bash",
                "get_job_status",
                "kill_job",
                "web_fetch",
                "web_search",
            ]

    async def close(self) -> None:
        """Close the MCP session."""
        if self.session:
            # Session cleanup handled by context manager
            pass
