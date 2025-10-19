#!/usr/bin/env python3
"""Standalone MCP Server - Run this separately from the agent."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.server import create_server


async def main_async():
    """Start the MCP server standalone."""
    print("=" * 70)
    print("MCP Server - Claude Agent System")
    print("=" * 70)
    print()
    print("Starting MCP server on http://localhost:8000")
    print()
    print("Endpoints:")
    print("  - MCP SSE endpoint:  http://localhost:8000/sse")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()

    # Create and run server
    server = create_server(config_dir="config")
    await server.run_server(host="0.0.0.0", port=8000)


def main():
    """Entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
