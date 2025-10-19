# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies
poetry install

# Run the system
poetry run python main.py
# Or use the poetry script
poetry run claude-agent

# Testing
poetry run pytest                    # Run all tests
poetry run pytest -v                 # Verbose output
poetry run pytest path/to/test.py    # Run specific test file

# Code Quality
poetry run black .                   # Format code
poetry run ruff check .              # Lint code
poetry run mypy .                    # Type check

# MCP Server standalone (for debugging)
poetry run python mcp_server/server.py
```

## System Architecture

This is a **three-layer agentic system** that combines an MCP tool server, an Ollama-powered agent with reasoning capabilities, and a terminal interface.

### Architecture Flow
```
User Input → Terminal CLI → Agent Core → MCP Server → Tools (File, Search, Shell, Web)
                   ↓             ↓              ↓
              Renderer    Ollama Client    Permission Manager
                              ↓
                     Think→Plan→Act→Observe→Reflect Loop
```

### Layer Responsibilities

1. **MCP Server** (`mcp_server/`)
   - Provides Claude Code-like tools via FastMCP: `read_file`, `write_file`, `edit_file`, `grep`, `glob`, `bash`, `web_fetch`, etc.
   - Tools are registered using `@self.mcp.tool()` decorator pattern
   - Each tool class (FileTools, SearchTools, ShellTools, WebTools) validates inputs and checks permissions before execution
   - Exposes SSE endpoint at `/sse` for MCP communication
   - Can run standalone on port 8000 for debugging

2. **Agent Core** (`agent/`)
   - Implements agentic loop: **Think → Plan → Act → Observe → Reflect**
   - Uses Ollama for LLM capabilities (supports model switching via `/model` command)
   - Can toggle between agent mode (full loop) and direct mode (simple chat)
   - Components:
     - `agent_core.py`: Main agentic loop orchestration
     - `ollama_client.py`: Ollama API integration
     - `context_manager.py`: Conversation history with truncation/summarization
     - `error_recovery.py`: Automatic retry with intelligent fixes
     - `tool_executor.py`: HTTP client for MCP tool execution
     - `prompts/system_prompt.py`: Phase-specific system prompts

3. **Terminal CLI** (`cli/`)
   - Interactive prompt using prompt_toolkit
   - Slash commands: `/model`, `/agent`, `/tools`, `/config`, `/permissions`, `/help`
   - Rich rendering with syntax highlighting via `cli/renderer.py`
   - Command handling in `cli/commands.py`

## Configuration System

All behavior is controlled via YAML files in `config/`:

- **`agent_config.yaml`**: Agent loop configuration, Ollama settings, error recovery strategies
- **`tools_config.yaml`**: Rate limits, tool-specific settings, logging configuration
- **`permissions_config.yaml`**: Directory access rules, blocked commands, permission modes

### Configuration Loading Pattern
```python
# Configs are loaded in main.py and passed down through layers
config = load_config()  # Combines all 3 YAML files
agent = AgentCore(config)
mcp_server = MCPServer(config_dir="config")
```

## Permission System

The `PermissionManager` (`mcp_server/permissions/access_control.py`) enforces security rules:

### Permission Modes
- **permissive**: Auto-approve most operations
- **moderate** (default): Approve safe directories, ask for sensitive operations
- **strict**: Require approval for all operations

### Directory Rules (config/permissions_config.yaml)
- `safe_directories`: Auto-approved (e.g., current project)
- `blocked_directories`: Always denied (e.g., `/etc`, `/sys`)
- `require_approval`: Must ask user before access

### Check Flow
```python
# Every tool operation checks permissions:
self.permission_manager.check_file_access(path, operation="read")  # or "write", "delete"
self.permission_manager.check_command(command)
self.permission_manager.check_url_access(url)
```

## Tool Implementation Pattern

All MCP tools follow this structure:

```python
async def tool_name(params...) -> Dict[str, Any]:
    try:
        # 1. Validate inputs
        validated = InputValidator.validate_file_path(file_path)

        # 2. Check permissions
        self.permission_manager.check_file_access(validated, operation="...")

        # 3. Execute operation
        result = await perform_operation()

        # 4. Return success response
        return {
            "success": True,
            "field1": value1,
            "field2": value2,
        }
    except Exception as e:
        # 5. Return error response
        return create_error_response(e)
```

### Tool Response Structure
```python
# Success
{"success": True, "file_path": "...", "content": "...", ...}

# Error
{"success": False, "error": {...}, "suggestions": [...]}
```

## Agentic Loop Phases

Each phase can be enabled/disabled in `agent_config.yaml` under `loop.phases`:

1. **Think**: Analyze request, determine what's needed (`_think()`)
2. **Plan**: Create step-by-step action plan (`_plan()`)
3. **Act**: Execute tool calls via MCP server (`_act()`)
4. **Observe**: Check results, detect errors (`_observe()`)
5. **Reflect**: Learn from outcomes, update strategy (`_reflect()`)

### Loop Control
- `max_steps`: Maximum iterations before stopping (default: 10)
- `verbose`: Show phase outputs in terminal
- Loop exits when plan contains "task complete" or observation marks task as complete

## Error Recovery System

The `ErrorRecoverySystem` (`agent/error_recovery.py`) automatically retries failed operations:

### Recovery Strategies (agent_config.yaml)
```yaml
error_recovery:
  strategies:
    permission_denied:
      action: "request_approval"
      auto_retry: true
    file_not_found:
      action: "search_alternatives"
      auto_retry: true
    syntax_error:
      action: "fix_and_retry"
      auto_retry: true
    network_error:
      action: "exponential_backoff"
      auto_retry: true
```

## Context Management

The `ContextManager` (`agent/context_manager.py`) handles conversation history:

- **Max messages**: Configurable limit (default: 100)
- **Truncation**: Keeps recent messages when limit exceeded
- **Summarization**: Optional compression of old context
- **Persistence**: Saves to `~/.claude-agent/history/` as JSON

### Message Format
```python
{"role": "user|assistant|system", "content": "..."}
```

## Adding New Tools

To add a new MCP tool:

1. **Implement in appropriate tool class** (`mcp_server/tools/`)
2. **Register in `mcp_server/server.py`** using `@self.mcp.tool()` decorator
3. **Add configuration** to `config/tools_config.yaml` if needed
4. **Update permissions** in `config/permissions_config.yaml` if sensitive

Example:
```python
# In mcp_server/server.py
@self.mcp.tool()
async def new_tool(param: str, optional: Optional[int] = None):
    """Tool description for MCP schema."""
    return await self.appropriate_tools.new_tool(param, optional)
```

## Important Notes

- **Ollama must be running** on localhost:11434 (configurable via `agent_config.yaml`)
- The system **auto-discovers Ollama models** on startup
- **Agent mode toggle**: `/agent on|off` switches between full agentic loop and simple LLM chat
- **Model switching**: `/model <name>` changes Ollama model at runtime
- **Conversation history** is automatically saved on exit to `~/.claude-agent/history/`
- All file operations create **backups** by default (configurable in `tools_config.yaml`)
