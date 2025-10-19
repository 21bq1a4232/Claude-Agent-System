# Claude Agent System

An intelligent agentic system with MCP (Model Context Protocol) tools, Ollama-powered agent, and a terminal interface similar to Claude Code.

## Architecture

```
Terminal CLI ──┬──> Direct Mode (Tools directly)
               └──> Agent Mode (Ollama) ──> MCP Server (Tools)
```

### Components

1. **MCP Server** - Provides Claude Code-like tools (Read, Write, Edit, Grep, Glob, Bash, WebFetch, etc.)
2. **Ollama Agent** - Intelligent agent with reasoning, error recovery, and tool orchestration
3. **Terminal CLI** - Interactive interface with slash commands and rich rendering

## Features

- **Dynamic Configuration** - YAML-based, no hardcoding
- **Intelligent Permission System** - Asks for approval on sensitive operations
- **Error Recovery** - Automatically retries with intelligent fixes
- **Multi-Model Support** - Switch between Ollama models
- **Universal Task Support** - Coding, research, file management, and more

## Installation

```bash
cd claude-agent-system
poetry install
```

## Usage

```bash
# Start the system
poetry run python main.py

# Or using the installed script
poetry run claude-agent
```

### Terminal Commands

- `/model <name>` - Switch Ollama model
- `/agent on|off` - Toggle agent mode
- `/tools` - List available MCP tools
- `/config` - Show/edit configuration
- `/permissions` - Manage permissions
- `/history` - View conversation history
- `/help` - Show help

## Configuration

Edit YAML files in `config/`:
- `agent_config.yaml` - Agent behavior and model settings
- `tools_config.yaml` - Tool configurations and rate limits
- `permissions_config.yaml` - Directory access and security rules

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint
poetry run ruff check .

# Type check
poetry run mypy .
```

## Examples

### Agent Mode (with reasoning)
```
>>> /agent on
>>> Read all Python files and summarize the architecture

[Agent] Planning: 1) Glob for .py files 2) Read key files 3) Summarize
[Agent] Executing: Glob("**/*.py")
[Tool] Found 47 files
[Agent] Summary: Architecture follows...
```

### Direct Mode
```
>>> /agent off
>>> Read main.py

[Tool] Reading /home/user/project/main.py...
[Content displayed]
```

## License

MIT License
