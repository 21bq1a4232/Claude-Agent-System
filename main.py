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


async def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code
    """
    print("=" * 60)
    print("Claude Agent System v0.1.0")
    print("=" * 60)
    print()

    # Load configuration
    try:
        config = load_config()
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    # Start terminal interface
    try:
        await run_terminal_interface(config)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cli_main() -> None:
    """CLI entry point for poetry script."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_main()
