"""Tool executor for MCP tools."""

import httpx
import json
from typing import Any, Dict, List, Optional
from httpx_sse import aconnect_sse


class ToolExecutor:
    """Executor for MCP tools via HTTP."""

    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        """
        Initialize tool executor.

        Args:
            mcp_server_url: URL of the MCP server
        """
        self.mcp_server_url = mcp_server_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)
        self._session_id = None

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
            # Build MCP tool call request
            request_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            }

            # Make request to MCP server via SSE endpoint
            response_data = None
            async with aconnect_sse(
                self.client,
                "POST",
                f"{self.mcp_server_url}/sse",
                json=request_payload,
            ) as event_source:
                async for event in event_source.aiter_sse():
                    # Parse SSE event data
                    if event.data:
                        response_data = json.loads(event.data)
                        # Get the first response (tool result)
                        break

            # Parse response
            if response_data and "result" in response_data:
                result = response_data["result"]

                # Check if tool execution was successful
                if result.get("success", True):
                    return {
                        "tool": tool_name,
                        "arguments": arguments,
                        "result": result,
                        "success": True,
                    }
                else:
                    return {
                        "tool": tool_name,
                        "arguments": arguments,
                        "error": result.get("error", "Unknown error"),
                        "result": result,
                        "success": False,
                    }
            else:
                # Handle error response
                error_msg = response_data.get("error", {}) if response_data else {}
                return {
                    "tool": tool_name,
                    "arguments": arguments,
                    "error": error_msg.get("message", "No response from MCP server"),
                    "success": False,
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
            # Try to get tools from server info endpoint
            response = await self.client.get(f"{self.mcp_server_url}/")
            if response.status_code == 200:
                data = response.json()
                return data.get("tools", [])

            # Fallback: try MCP protocol
            request_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            }

            async with aconnect_sse(
                self.client,
                "POST",
                f"{self.mcp_server_url}/sse",
                json=request_payload,
            ) as event_source:
                async for event in event_source.aiter_sse():
                    if event.data:
                        response_data = json.loads(event.data)
                        if "result" in response_data:
                            tools = response_data["result"].get("tools", [])
                            return [tool.get("name") for tool in tools]
                        break

            return []

        except Exception:
            # Fallback to known tools if server is not available
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
        """Close the HTTP client."""
        await self.client.aclose()
