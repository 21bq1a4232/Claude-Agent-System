"""Web operation tools (WebFetch, WebSearch)."""

import httpx
from typing import Any, Dict, Optional
from mcp_server.permissions import PermissionManager, InputValidator
from mcp_server.utils import get_logger, NetworkError, TimeoutError, create_error_response


logger = get_logger(__name__)


class WebTools:
    """Web operation tools."""

    def __init__(self, permission_manager: PermissionManager, config: Dict[str, Any]):
        """
        Initialize web tools.

        Args:
            permission_manager: Permission manager instance
            config: Tool configuration
        """
        self.permission_manager = permission_manager
        self.config = config.get("tools", {})

    async def web_fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Fetch content from a URL.

        Args:
            url: URL to fetch
            method: HTTP method
            headers: HTTP headers
            timeout: Request timeout

        Returns:
            Dictionary with response content
        """
        try:
            # Validate URL
            url = InputValidator.validate_url(url)

            # Check permissions
            self.permission_manager.check_url_access(url)

            # Get config
            fetch_config = self.config.get("web_fetch", {})
            timeout = timeout or fetch_config.get("timeout", 30)
            max_size_mb = fetch_config.get("max_content_size_mb", 10)
            user_agent = fetch_config.get("user_agent", "ClaudeAgentSystem/0.1.0")

            # Prepare headers
            request_headers = {"User-Agent": user_agent}
            if headers:
                request_headers.update(headers)

            # Fetch
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=fetch_config.get("max_redirects", 5),
            ) as client:
                try:
                    response = await client.request(
                        method,
                        url,
                        headers=request_headers,
                    )
                except httpx.TimeoutException:
                    raise TimeoutError(f"Request timed out after {timeout} seconds", timeout=timeout)
                except httpx.NetworkError as e:
                    raise NetworkError(f"Network error: {str(e)}", url=url)

            # Check size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                raise NetworkError(
                    f"Content too large: {int(content_length) / (1024 * 1024):.2f}MB (max: {max_size_mb}MB)",
                    url=url,
                )

            # Get content
            content = response.text

            return {
                "success": True,
                "url": url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": content,
                "content_length": len(content),
            }

        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return create_error_response(e)

    async def web_search(
        self,
        query: str,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Search the web (simplified implementation).

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            Dictionary with search results
        """
        try:
            # Get config
            search_config = self.config.get("web_search", {})
            max_results = min(max_results, search_config.get("max_results", 10))

            # Note: This is a placeholder implementation
            # In a real implementation, you would integrate with a search API
            # (DuckDuckGo, Google Custom Search, etc.)

            return {
                "success": True,
                "query": query,
                "results": [],
                "message": "Web search not yet fully implemented. Use web_fetch to fetch specific URLs.",
            }

        except Exception as e:
            logger.error(f"Error searching web: {e}")
            return create_error_response(e)
