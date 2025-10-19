"""Tests for ToolExecutor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent.tool_executor import ToolExecutor


@pytest.fixture
def tool_executor():
    """Create a ToolExecutor instance."""
    return ToolExecutor("http://localhost:8000")


@pytest.mark.asyncio
async def test_tool_executor_initialization():
    """Test ToolExecutor initialization."""
    executor = ToolExecutor("http://localhost:8000")
    assert executor.mcp_server_url == "http://localhost:8000"
    assert executor.client is not None


@pytest.mark.asyncio
async def test_execute_tool_success(tool_executor):
    """Test successful tool execution."""
    # Mock SSE response
    mock_event = MagicMock()
    mock_event.data = '{"result": {"success": true, "content": "test content"}}'

    async def mock_aiter_sse():
        yield mock_event

    with patch("agent.tool_executor.aconnect_sse") as mock_sse:
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value.aiter_sse = mock_aiter_sse
        mock_sse.return_value = mock_context

        result = await tool_executor.execute_tool(
            "read_file", {"file_path": "/test/file.txt"}
        )

        assert result["success"] is True
        assert result["tool"] == "read_file"
        assert "result" in result


@pytest.mark.asyncio
async def test_execute_tool_error(tool_executor):
    """Test tool execution with error."""
    with patch("agent.tool_executor.aconnect_sse") as mock_sse:
        mock_sse.side_effect = Exception("Connection failed")

        result = await tool_executor.execute_tool(
            "read_file", {"file_path": "/test/file.txt"}
        )

        assert result["success"] is False
        assert "error" in result


@pytest.mark.asyncio
async def test_list_tools_fallback(tool_executor):
    """Test list_tools fallback when server is unavailable."""
    with patch.object(tool_executor.client, "get") as mock_get:
        mock_get.side_effect = Exception("Connection failed")

        tools = await tool_executor.list_tools()

        assert isinstance(tools, list)
        assert "read_file" in tools
        assert "write_file" in tools


@pytest.mark.asyncio
async def test_list_tools_from_server(tool_executor):
    """Test list_tools from server endpoint."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tools": ["read_file", "write_file", "grep", "bash"]
    }

    with patch.object(tool_executor.client, "get", return_value=mock_response):
        tools = await tool_executor.list_tools()

        assert tools == ["read_file", "write_file", "grep", "bash"]


@pytest.mark.asyncio
async def test_close(tool_executor):
    """Test closing the executor."""
    with patch.object(tool_executor.client, "aclose") as mock_close:
        await tool_executor.close()
        mock_close.assert_called_once()
