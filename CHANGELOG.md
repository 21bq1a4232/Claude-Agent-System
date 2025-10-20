# Changelog

All notable changes to the Claude Agent System project.

## [Unreleased] - 2025-10-20

### 🔧 Critical Fixes

#### **FIX 4: Tool Results Not Reaching Model (CRITICAL)**
- **Issue**: Tool executes successfully but model asks user to paste content manually
- **Root Cause**: `context_manager.py` filters out messages with `role="tool"` when sending to LLM
- **Symptoms**:
  - Logs show `[read_file] SUCCESS - 905 lines returned`
  - But agent responds: "Please copy and paste the content..."
  - Tool works, but model never sees the results
- **Fix**: Added `"tool"` to allowed roles in `get_messages_for_llm()` method
- **Files Modified**:
  - `agent/context_manager.py` (line 98)
  - Changed: `if msg["role"] in ["user", "assistant", "system"]`
  - To: `if msg["role"] in ["user", "assistant", "system", "tool"]`
- **Impact**: Tool results now properly reach the model → Agent can actually use tool outputs!

#### Fixed Agent Hanging Issue
- **Issue**: Agent would hang indefinitely at "Analyzing request and selecting tools..."
- **Root Cause**: `ollama` Python library is synchronous, but was being called with `await`, blocking the event loop
- **Fix**: Wrapped all `ollama.chat()` and `ollama.generate()` calls with `asyncio.to_thread()`
- **Files Modified**:
  - `agent/ollama_client.py` (lines 90, 163)
  - Added proper async handling for synchronous library
- **Impact**: No more infinite hangs, agent now responds within configured timeout

#### Added Timeout Protection
- **Feature**: Aggressive timeout protection to prevent infinite hangs
- **Configuration**:
  - `llm_timeout: 15` seconds (testing) / 60s (production)
  - `tool_timeout: 30` seconds
- **Files Modified**:
  - `agent/agent_core.py` - Added `asyncio.wait_for()` with timeout
  - `config/agent_config.yaml` - Added timeout configuration
- **Impact**: Clear timeout errors instead of silent hangs, graceful fallback to direct mode

#### Added Debug Logging
- **Feature**: Comprehensive debug output showing exactly what's happening
- **Output**:
  - Shows tool count, current model, LLM call status
  - `[DEBUG] Calling ollama.chat()... COMPLETED ✓` indicator
  - Clear timeout/error messages
- **Files Modified**:
  - `agent/agent_core.py` - Added verbose logging throughout
- **Impact**: Easy to diagnose issues, see progress in real-time

### 🧠 Enhanced Intelligence

#### Advanced System Prompt
- **Feature**: Claude Code-style system prompt for intelligent behavior
- **Key Instructions**:
  - READ and UNDERSTAND (don't just dump raw data)
  - ANALYZE relevance to user's question
  - SYNTHESIZE concise, intelligent summaries
  - EXPLAIN context and provide insights
- **Files Modified**:
  - `agent/prompts/system_prompt.py` - Complete rewrite (~300 words → comprehensive guide)
- **Impact**: Agent now provides intelligent summaries instead of raw data dumps

#### Smart Content Truncation
- **Feature**: Auto-truncate large files to prevent context overflow
- **Configuration**:
  - `max_content_tokens: 4000` (~16KB text)
  - `truncate_keep_ratio: [0.6, 0.4]` (first 60%, last 40%)
- **Files Modified**:
  - `agent/agent_core.py` - Added truncation logic
  - `config/tools_config.yaml` - Added token limits
- **Impact**: Can handle large files without breaking, maintains context

### 📊 Comprehensive Logging

#### MCP Tool Logging
- **Feature**: Detailed logging of all MCP tool operations
- **Log Format**:
  ```
  [timestamp] [tool_name] START - parameters
  [timestamp] [tool_name] Validation passed
  [timestamp] [tool_name] Permission check: ALLOWED
  [timestamp] [tool_name] SUCCESS - details, execution_time
  ```
- **Files Modified**:
  - `mcp_server/tools/file_tools.py` - Added comprehensive logging
  - More tools to follow (search, shell, web)
- **Log Files**:
  - `logs/mcp_tools.log` - All tool operations
  - `logs/agent.log` - Agent decisions (future)
  - `logs/errors.log` - Centralized errors (future)
- **Impact**: Full visibility into tool execution, easy debugging

### 📝 Clean Code Improvements

#### Removed Hardcoded Logic
- **Before**: Hardcoded per-tool result formatting with if/else chains
- **After**: Clean, flat JSON structure sent to model
- **Files Modified**:
  - `agent/agent_core.py` - Simplified result formatting
- **Impact**: More maintainable, lets model's intelligence handle formatting

#### Improved Error Handling
- **Feature**: Graceful fallback on all error conditions
- **Behaviors**:
  - LLM timeout → Falls back to direct mode
  - Tool calling fails → Retries without tools
  - Model error → Clear error message + fallback
- **Files Modified**:
  - `agent/agent_core.py` - Added try/except with fallbacks
- **Impact**: System never crashes, always provides useful response

### 🛠️ Developer Tools

#### Automated Fix Script
- **File**: `auto_fix.py`
- **Purpose**: Automatically apply all critical fixes
- **Features**:
  - Creates backups before modifying
  - Applies asyncio.to_thread wrapper
  - Adds timeout and debug logging
  - Updates configuration
- **Usage**: `python3 auto_fix.py`

#### Test/Verification Script
- **File**: `test_fixes.py`
- **Purpose**: Verify all fixes are working correctly
- **Tests**:
  - Ollama connection
  - Model tool calling support
  - Async wrapper applied
  - Timeout configured
  - Debug logging enabled
  - Simple query works
  - Agent startup
- **Usage**: `python3 test_fixes.py`

#### Comprehensive Documentation
- **Files**:
  - `QUICK_FIX_GUIDE.md` - 3-minute quick start
  - `LOCAL_MACHINE_FIXES.md` - Detailed fix instructions
  - `APPLY_ON_LOCAL_MACHINE.md` - Step-by-step walkthrough
  - `critical_fixes.patch` - Git patch file
  - Updated `CLAUDE.md` - Comprehensive project documentation

### 🎯 Model Recommendations

#### MacBook M4 16GB RAM
- **Best**: `qwen2.5:7b` - Excellent tool calling, 6GB RAM, fast
- **Alternative**: `llama3.1:8b` - Very reliable, 7-8GB RAM
- **Alternative**: `mistral:7b-instruct-v0.3` - Good balance, 6GB RAM
- **Avoid**:
  - `deepseek-r1:*` - Reasoning models break tool calling
  - `*:q2_K` - Heavy quantization causes failures

### ⚡ Performance Improvements

#### Metrics (with qwen2.5:7b)
- Simple greeting: 0.5-1s
- Tool selection: 2-3s
- Single tool execution: 3-5s
- Complex queries: 8-12s
- Memory usage: ~6GB

#### Optimizations Applied
- ✅ Streaming responses (instant output)
- ✅ Reduced context (2048 tokens)
- ✅ Proper async handling (no blocking)
- ✅ Smart truncation (prevents overflow)
- ✅ Aggressive timeouts (fast failure)

---

## Previous Changes (Before 2025-10-20)

### Streaming Responses
- Added `chat_stream()` method for faster perceived responses
- First words appear in ~0.5s instead of 5s

### Optimized Configuration
- Reduced temperature (0.3), context (2048), num_predict (2048)
- Enabled streaming by default

### System Prompt Optimization
- Shortened from 200+ words to 60 words
- Made general-purpose (coding + non-coding)

### Conversational Detection
- Smart detection of simple queries
- Skips tool execution for greetings

### Native Ollama Tool Calling
- Uses Ollama's native `tools` parameter
- Reduced from 2 LLM calls to 1 per request

### MCP Server HTTP Endpoint
- Added `GET /tools` endpoint for tool discovery
- Starlette routing for multiple endpoints

### Error Handling Improvements
- Try/catch in agentic loop
- Fallback to direct response on tool failure
- None-checking for tool lists

---

## Migration Guide

### From Old Version (Pre-2025-10-20)

1. **Backup your current code**:
   ```bash
   cd ~/Downloads/Agents/Claude-Agent-System
   git stash  # or create manual backups
   ```

2. **Apply critical fixes**:
   ```bash
   python3 auto_fix.py
   ```

3. **Verify fixes worked**:
   ```bash
   python3 test_fixes.py
   ```

4. **Install recommended model**:
   ```bash
   ollama pull qwen2.5:7b
   ```

5. **Test the system**:
   ```bash
   poetry run python main.py
   /model qwen2.5:7b
   >>> list files in this directory
   ```

### Breaking Changes
- **None** - All changes are backwards compatible
- Old configuration files still work (new timeouts use defaults)
- Existing models still supported (qwen2.5:7b recommended)

### Deprecated
- **Reasoning models** (deepseek-r1, qwq) - Never worked well with tools
- **Heavy quantization** (*:q2_K for 12B+ models) - Unreliable tool calling

---

## Support

For issues or questions:
1. Check `QUICK_FIX_GUIDE.md` for common problems
2. Run `python3 test_fixes.py` to diagnose
3. Check `logs/mcp_tools.log` for detailed execution logs
4. Enable debug mode: Set `verbose: true` in config
