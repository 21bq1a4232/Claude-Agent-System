"""Main entry point for Claude Agent System."""

import asyncio
import sys
import yaml
from pathlib import Path
from cli.interface import run_terminal_interface


def load_config(config_dir: str = "config") -> dict:
    """
    Load configuration from YAML files.

    Args:
        config_dir: Directory containing config files

    Returns:
        Combined configuration dictionary
    """
    config_path = Path(config_dir)
    config = {}

    config_files = {
        "agent": "agent_config.yaml",
        "tools": "tools_config.yaml",
        "permissions": "permissions_config.yaml",
    }

    for key, filename in config_files.items():
        file_path = config_path / filename
        try:
            with open(file_path, "r") as f:
                loaded = yaml.safe_load(f)
                if key == "agent":
                    config.update(loaded)
                else:
                    config[key + "_config"] = loaded
        except Exception as e:
            print(f"Warning: Failed to load {filename}: {e}", file=sys.stderr)

    return config


async def check_mcp_server(url: str = "http://localhost:8000") -> bool:
    """Check if MCP server is running by testing SSE endpoint."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            # Try to connect to SSE endpoint (will return 405 if server is up but wrong method)
            response = await client.get(f"{url}/sse", timeout=2.0)
            # Any response (even error) means server is running
            return True
    except httpx.ConnectError:
        return False
    except Exception:
        # Server responded (even with error) = it's running
        return True


async def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code
    """
    print("=" * 70)
    print("Claude Agent System v0.1.0")
    print("=" * 70)
    print()

    # Check MCP server
    print("Checking MCP server...")
    server_running = await check_mcp_server()

    if not server_running:
        print("⚠  MCP server not running!")
        print()
        print("Please start the MCP server first:")
        print("  Terminal 1: poetry run claude-agent-server")
        print("  Terminal 2: poetry run claude-agent")
        print()
        print("Or use: poetry run python start_server.py")
        print()
        return 1

    print("✓ MCP server is running")

    # Load configuration
    try:
        config = load_config()
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"✗ Error loading configuration: {e}", file=sys.stderr)
        return 1

    # Check Ollama
    print("Checking Ollama connection...")
    try:
        import ollama
        models = ollama.list()
        model_count = len(models.get("models", []))
        print(f"✓ Ollama connected ({model_count} models available)")
    except Exception as e:
        print(f"⚠  Ollama not available: {e}")
        print("  Make sure Ollama is running: ollama serve")

    print()

    # Start terminal interface
    try:
        await run_terminal_interface(config)
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cli_main() -> None:
    """CLI entry point for poetry script."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_main()
