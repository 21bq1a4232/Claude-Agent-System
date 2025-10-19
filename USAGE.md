# Claude Agent System - Usage Guide

## Quick Start

The system has two components that run separately for better debugging and logging:

1. **MCP Server** - Provides tools (file, search, shell, web operations)
2. **Agent** - Intelligent assistant that uses the tools

### Running the System

**Terminal 1 - Start MCP Server:**
```bash
poetry run claude-agent-server
```

You should see:
```
======================================================================
MCP Server - Claude Agent System
======================================================================

Starting MCP server on http://localhost:8000

Endpoints:
  - Health check:  http://localhost:8000/health
  - Server info:   http://localhost:8000/
  - MCP endpoint:  http://localhost:8000/sse

Press Ctrl+C to stop
======================================================================

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Terminal 2 - Start Agent:**
```bash
poetry run claude-agent
```

You should see:
```
======================================================================
Claude Agent System v0.1.0
======================================================================

Checking MCP server...
✓ MCP server is running
✓ Configuration loaded
Checking Ollama connection...
Auto-selected model: mistral-nemo:12b-instruct-2407-q2_K
✓ Ollama connected (3 models available)

╭──────────────────────────────────────────────────────────────────╮
│ Claude Agent System                                              │
│ An intelligent assistant with MCP tools and Ollama               │
╰──────────────────────────────────────────────────────────────────╯
ℹ Type /help for available commands, or just chat naturally
───────────────────────────────────────────────────────────────────
>>>
```

## Available Commands

```
/help              - Show help message
/model [name]      - Switch Ollama model or list available
/agent on|off      - Toggle agent mode
/tools             - List available MCP tools
/config [key]      - Show configuration
/history [limit]   - View conversation history
/clear             - Clear conversation history
/permissions       - View/manage permissions
/exit or /quit     - Exit the application
```

## Example Usage

### List Models
```
>>> /model
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                        Available Models                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
→ llama3.2:3b
  mistral:7b
  qwen2:0.5b
```

### List Files
```
>>> list files in this directory
🤔 Processing your request...

[Act] list_directory - ✓

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
Files in current directory:
- agent/
- cli/
- config/
- mcp_server/
- tests/
- main.py
- pyproject.toml
- README.md
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Read a File
```
>>> read main.py
🤔 Processing your request...

[Act] read_file - ✓

[Shows file content with syntax highlighting]
```

## Debugging

### See MCP Tool Logs

The MCP server terminal shows all tool invocations:
```
INFO:     127.0.0.1:52345 - "POST /sse HTTP/1.1" 200 OK
INFO:     Tool called: list_directory(directory=".", pattern=None)
INFO:     Tool result: success=True, items=15
```

### See Agent Reasoning

When verbose mode is on (default), you'll see the agent's tool selection:
```
[Act] list_directory - ✓
```

### Test Server Manually

Check if server is running:
```bash
curl http://localhost:8000/health
```

List available tools:
```bash
curl http://localhost:8000/
```

## Model Recommendations

Models are **auto-discovered** from Ollama on startup. No configuration needed!

**Recommended models (in order):**
1. `qwen2.5:3b` or `qwen2.5:7b` - Best balance
2. `llama3.2:3b` - Good instruction following
3. `mistral:7b` - Reliable but larger
4. `qwen2:0.5b` - Smallest/fastest

**Avoid:** Reasoning models like `deepseek-r1` - they output thinking process which causes hallucinations.

## Configuration

Edit files in `config/`:
- `agent_config.yaml` - Agent behavior (loops disabled for better performance)
- `tools_config.yaml` - Tool settings and rate limits
- `permissions_config.yaml` - Security and access control

All paths use **dynamic variables**:
- `${CWD}` - Current working directory
- `${HOME}` - User home directory

No hardcoded paths!

## Troubleshooting

### "MCP server not running"
Start the server first:
```bash
poetry run claude-agent-server
```

### "Error listing models: 'name'"
This is fixed! Models are now auto-discovered with fallback handling.

### "Ollama not available"
Start Ollama:
```bash
ollama serve
```

### Agent gives weird responses
- Make sure you're not using a reasoning model (like deepseek-r1)
- Try switching models: `/model llama3.2:3b`
- Check that Think/Plan phases are disabled in config (they are by default)

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Terminal 1     │         │   Terminal 2     │
│                 │         │                  │
│  MCP Server     │◄────────│   Agent          │
│  (Port 8000)    │  HTTP   │   (Ollama)       │
│                 │         │                  │
│  • File tools   │         │  • User input    │
│  • Search tools │         │  • Tool select   │
│  • Shell tools  │         │  • Response gen  │
│  • Web tools    │         │                  │
└─────────────────┘         └──────────────────┘
```

## Performance

- **Agent loop simplified** - No unnecessary Think/Plan phases
- **Direct tool execution** - Request → Tool Selection → Execute → Done
- **Separate processes** - Server and agent run independently
- **Verbose logging** - See exactly what's happening

Typical response time: <2 seconds for simple requests
