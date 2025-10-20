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

## Recent Optimizations & Fixes (2025-10-20 - Latest Session)

### Critical Fixes

**Streaming Response Implementation:**
- Fixed async/sync confusion - ollama library is **synchronous**, not async
- Changed `async for` to `for` in streaming code
- Result: No more hanging on responses
- Files modified: `agent/ollama_client.py`, `agent/agent_core.py`

**MCP Tool Result Parsing:**
- Fixed MCP `CallToolResult` parsing - it returns content as list of text items
- Properly extracts and parses JSON from MCP responses
- Handles both JSON and text responses gracefully
- File: `agent/tool_executor.py`

**Tool Result Post-Processing:**
- Tool results now formatted as structured JSON before sending to model
- Model receives clear instruction: "format this data in a user-friendly way"
- Result: Clean, formatted output instead of raw JSON garbage
- Example: "Here are the files:\n- main.py\n- README.md" instead of "{'na_name': '.DS_Store'}..."
- File: `agent/agent_core.py`

**Conversational Detection (Dynamic):**
- Removed hardcoded tool patterns
- Only detects obvious greetings ("hi", "hello", "thanks")
- Everything else goes to model with tools - model decides!
- Result: Truly dynamic tool selection based on model intelligence
- File: `agent/agent_core.py`

### Key Architecture Changes

**Everything is Dynamic Now:**
```python
# OLD: Hardcoded patterns
tool_patterns = ["list", "show", "read", "write", ...]  # ❌ Static

# NEW: Model decides
if message in ["hi", "hello", "thanks"]:  # Only obvious greetings
    return conversational
else:
    send_to_model_with_tools()  # ✅ Model decides everything!
```

**Streaming Flow:**
```python
# Ollama library is SYNCHRONOUS
for chunk in ollama.chat_stream(messages):  # Not async for!
    print(chunk, end="", flush=True)
```

**Tool Result Processing:**
```python
# Format results properly
tool_results_json = json.dumps(tool_results, indent=2)
context.add_message("system", f"Tool results:\n{tool_results_json}\n\nFormat nicely for user.")

# Model processes and formats
model.stream_response()  # → Clean output!
```

## Recent Optimizations (2025-10-20)

### Performance & Speed Improvements

**Streaming Responses (Fast like `ollama run`):**
- Added `chat_stream()` method to `OllamaClient` for streaming responses
- Modified `_direct_response()` to use streaming for instant perceived responses
- Configuration: `stream_responses: true` in `agent_config.yaml`
- **Result**: First words appear in ~0.5s instead of 5s

**Optimized Configuration:**
```yaml
# agent_config.yaml optimizations:
stream_responses: true          # Enable streaming
temperature: 0.3                # Reduced from 0.7 (faster, more deterministic)
max_context_tokens: 2048        # Reduced from 4096 (faster processing)
num_predict: 2048              # Limited from -1 (prevents runaway)
max_messages: 20               # Reduced from 100 (less memory)
```

**System Prompt Optimization:**
- Shortened from 200+ words to 60 words (70% reduction)
- Made general-purpose (coding + non-coding tasks)
- Still includes essential directory guidance ("this directory" = ".")
- Located in `agent/prompts/system_prompt.py`

### Conversational Detection

**Smart Tool Selection:**
- Agent detects conversational messages ("hi", "thanks", "what is...") 
- Skips tool execution loop for simple chat
- Uses direct streaming response for instant replies
- Method: `_is_conversational()` in `agent_core.py`

### Native Ollama Tool Calling

**Single LLM Call Instead of Two:**
- Uses Ollama's native `tools` parameter for function calling
- Model decides: use tool OR respond directly
- Reduced from 2 LLM calls to 1 per request
- **Result**: ~50% faster for tool-requiring tasks

**Tool Definitions:**
- Tool schemas defined in `_get_tools_for_ollama()` 
- Includes descriptions with examples for proper usage
- Example: "this directory" → directory="."
- Helps model understand correct parameters

### Error Handling Improvements

**Robust Error Handling:**
- Added try/catch in agentic loop for graceful failures
- Fallback to direct response if tool calling fails
- None-checking for tool lists and responses
- Better error messages for debugging

**Common Fixes:**
- `'NoneType' object is not iterable` → Fixed with None checks
- `object async_generator can't be used in 'await'` → Fixed async/await usage
- Model doesn't support tools → Auto-fallback to chat mode

### MCP Server Enhancements

**New HTTP Endpoint:**
- Added `GET /tools` endpoint for listing available tools
- Returns: `{"success": true, "tools": ["read_file", ...], "count": 12}`
- Used by agent for dynamic tool discovery
- Implementation in `mcp_server/server.py` using Starlette routing

### Tool Descriptions (Claude Code-like)

**Improved Tool Descriptions:**
- Clear examples in descriptions
- Explicit path guidance ("." for current directory)
- Better parameter descriptions
- Helps model select correct tools and parameters

Example:
```python
"list_directory": {
    "description": "List files and directories. IMPORTANT: Use '.' for current directory.",
    "parameters": {
        "directory": {
            "type": "string",
            "description": "Directory path. Use '.' for current/this directory, '..' for parent"
        }
    }
}
```

## Important Notes

- **Ollama must be running** on localhost:11434 (configurable via `agent_config.yaml`)
- The system **auto-discovers Ollama models** on startup
- **Agent mode toggle**: `/agent on|off` switches between full agentic loop and simple LLM chat
- **Model switching**: `/model <name>` changes Ollama model at runtime
- **Conversation history** is automatically saved on exit to `~/.claude-agent/history/`
- All file operations create **backups** by default (configurable in `tools_config.yaml`)
- **Streaming enabled by default** for instant responses (like `ollama run`)
- **Best models for M4 MacBook (16GB RAM)**: qwen2.5:7b, mistral-nemo:12b, llama3.2:3b
- **Avoid reasoning models** (deepseek-r1, qwq) - they don't support tool calling

## Common Issues & Solutions

### Issue: Response hangs/freezes
**Cause**: Using `async for` with synchronous ollama library  
**Solution**: Use regular `for` loop - ollama is synchronous, not async

### Issue: Raw JSON output instead of formatted text
**Cause**: Not post-processing tool results  
**Solution**: Format results as JSON and instruct model to format nicely (already fixed)

### Issue: Tool not executing when asked
**Cause**: Hardcoded patterns missing the keyword  
**Solution**: Let model decide - only detect obvious greetings, send everything else to model with tools

### Issue: "does not support tools" error
**Cause**: Using reasoning model (deepseek-r1, qwq)  
**Solution**: Switch to mistral-nemo, qwen2.5, or llama3.2

### Issue: MCP tool execution fails
**Cause**: MCP result parsing incorrect  
**Solution**: Parse `CallToolResult.content` list properly (already fixed)

### Issue: Slow first response (~5s)
**Cause**: Not using streaming, large context  
**Solution**: Enable streaming + reduce context tokens (already fixed in config)

## Development Workflow

### Making Changes

1. **Modify code** in `agent/`, `mcp_server/`, or `cli/`
2. **Update CLAUDE.md** with significant changes
3. **Restart both servers**:
   - MCP Server: `poetry run python start_server.py`
   - Agent: `poetry run python main.py`
4. **Test** the changes
5. **Commit** with clear message

### Testing Checklist

```bash
# 1. Test conversational (no tools)
>>> hi
>>> thanks
>>> what is a REST API?

# 2. Test tool execution
>>> list files in this directory
>>> read README.md
>>> search for "TODO" in all files

# 3. Test model switching
>>> /model qwen2.5:7b
>>> /model mistral-nemo:12b-instruct-2407-q2_K

# 4. Test error handling
>>> read nonexistent_file.txt
```

### Debug Mode

Set `verbose: true` in `agent_config.yaml` to see:
- `[Agent]` - Agent decisions
- `[Act]` - Tool executions
- `[Act] Arguments:` - Tool parameters
- Error details and stack traces

## System State Summary (Current)

### What Works Now ✅

1. **Fast Streaming Responses**
   - First words appear in ~0.5s (like `ollama run`)
   - Proper sync/async handling
   - No hanging or freezing

2. **Dynamic Tool Selection**
   - Model decides what tools to use
   - No hardcoded patterns (except obvious greetings)
   - Supports all types of requests

3. **Clean Output Formatting**
   - Tool results post-processed by LLM
   - User-friendly formatted responses
   - No raw JSON in output

4. **General Purpose Assistant**
   - Handles coding tasks
   - Handles non-coding questions
   - File operations work correctly
   - Command execution works

5. **Proper Error Handling**
   - Graceful fallbacks
   - Clear error messages
   - Automatic retries where appropriate

### Configuration (Optimized)

```yaml
# agent_config.yaml - Current optimized settings
agent:
  stream_responses: true
  max_messages: 20
  tokens:
    max_context_tokens: 2048
    response_reserve: 512

ollama:
  temperature: 0.3
  num_predict: 2048
```

### Files Modified in Latest Session

1. `agent/agent_core.py`
   - Fixed streaming (sync not async)
   - Dynamic conversational detection
   - Tool result post-processing
   
2. `agent/ollama_client.py`
   - Changed `chat_stream()` to sync generator
   - Proper ollama library usage

3. `agent/tool_executor.py`
   - Fixed MCP result parsing
   - Handles content list properly

4. `agent/prompts/system_prompt.py`
   - Shortened to 60 words
   - General purpose (not just file ops)
   - Still includes directory guidance

5. `config/agent_config.yaml`
   - Enabled streaming
   - Reduced context/memory
   - Optimized for speed

6. `mcp_server/server.py`
   - Added `/tools` HTTP endpoint
   - Starlette routing for multiple endpoints

### Architecture Flow (Current)

```
User Input
    ↓
Is it "hi"/"hello"/"thanks"? 
    ↓ YES → Direct streaming response
    ↓ NO
Send to Model with Tools
    ↓
Model decides: Use tools or respond?
    ↓ Use tools
Execute tools via MCP
    ↓
Format results as JSON + instruction
    ↓
Model post-processes and formats
    ↓
Stream formatted response to user
```

### Performance Metrics

- **Simple greeting**: 0.5s (instant streaming)
- **Tool execution**: 5-8s (tool call + formatting)
- **Complex query**: 8-12s (multiple tools + formatting)
- **Memory usage**: ~6GB (mistral-nemo) / ~7GB (qwen2.5:7b)

### What's Still Hardcoded (Intentionally)

1. **Tool schemas** - Needed for Ollama's tool calling API
2. **MCP server URL** - Default localhost:8000 (configurable)
3. **Obvious greetings** - ["hi", "hello", "thanks"] for speed
4. **Ollama connection** - localhost:11434 (configurable)

Everything else is **dynamic and model-driven**!
