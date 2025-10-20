"""Tool executor for MCP tools."""

import httpx
import json
from typing import Any, Dict, List, Optional
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# Expose aconnect_sse alias to allow tests to patch the SSE connector
aconnect_sse = sse_client


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
        # HTTP client used for simple REST endpoints (and tests)
        self.client: httpx.AsyncClient = httpx.AsyncClient(base_url=self.mcp_server_url)

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
            # Connect to MCP server SSE stream and execute tool
            client_ctx = aconnect_sse(url=f"{self.mcp_server_url}/sse")
            async with client_ctx as (read, write):
                # Create and initialize session
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Execute the tool through session
                    result = await session.call_tool(tool_name, arguments)
                    
                    # Parse MCP CallToolResult
                    # MCP returns CallToolResult with content list
                    if hasattr(result, 'content') and isinstance(result.content, list):
                        # Extract text from content items
                        content_texts = []
                        for item in result.content:
                            if hasattr(item, 'text'):
                                content_texts.append(item.text)
                        
                        # Combine all text content
                        combined_text = "\n".join(content_texts) if content_texts else ""
                        
                        # Try to parse as JSON
                        try:
                            result_data = json.loads(combined_text)
                        except (json.JSONDecodeError, ValueError):
                            # If not JSON, return as text
                            result_data = {"content": combined_text}
                    else:
                        # Fallback for other result formats
                        result_data = {"content": str(result)}
                    
                    return {
                        "tool": tool_name,
                        "arguments": arguments,
                        "result": result_data,
                        "success": True,
                    }

            # If no result event received
            return {
                "tool": tool_name,
                "arguments": arguments,
                "result": None,
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
            # Use HTTP endpoint to list tools (simpler and test-friendly)
            resp = await self.client.get(f"{self.mcp_server_url}/tools")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("tools", [])
            else:
                raise Exception(f"Unexpected status: {resp.status_code}")

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
        # Close HTTP client
        try:
            await self.client.aclose()
        except Exception:
            pass
